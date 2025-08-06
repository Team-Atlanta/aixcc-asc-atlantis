use crate::generators::{generate_record, value_to_bytes};
use crate::parser::{Attribute, FieldType, Grammar, Record, RecordType};
use libafl::inputs::HasMutatorBytes;
use libafl::mutators::{MutationResult, Mutator};
use libafl::state::HasRand;
use libafl_bolts::Named;
use libafl_bolts::{rands::Rand, Error};
use std::borrow::Cow;
use std::collections::HashMap;

pub struct TestLangMutator(Grammar);

// TODO: ask about endianness
// TODO: move from string to cow
// TODO: make falliable in case another mutator makes a breaking change

impl TestLangMutator {
    pub fn new(grammar: Grammar) -> Self {
        Self(grammar)
    }
}

impl<I, S> Mutator<I, S> for TestLangMutator
where
    S: HasRand,
    I: HasMutatorBytes,
{
    fn mutate(&mut self, state: &mut S, input: &mut I) -> Result<MutationResult, Error> {
        if input.bytes().is_empty() {
            return Ok(MutationResult::Skipped);
        }

        let mut parsed_record = ParsedRecord::parse(input.bytes(), &self.0)?;
        let height_map = parsed_record.height_map();
        let depth_to_modify = state.rand_mut().below(height_map.len());
        let index_to_modify = state.rand_mut().below(height_map[depth_to_modify]);

        let record_to_modify = parsed_record
            .find_record(depth_to_modify, index_to_modify)
            .ok_or(Error::unsupported("invalid record"))?;
        let record_to_modify_type = &record_to_modify.name;

        let records = self.0.records();
        let root_record = records
            .get(record_to_modify_type)
            .ok_or(Error::unsupported("RECORD to modify not found"))?;

        let new_record = generate_record(state, root_record, &records)?;

        record_to_modify.size = new_record.len();
        record_to_modify.fields.clear();
        record_to_modify.fields.push((
            record_to_modify_type.clone(),
            ParsedField::Normal {
                name: "MODIFIED".to_string(),
                size: new_record.len(),
                value: new_record,
            },
        ));

        input
            .bytes_mut()
            .copy_from_slice(&parsed_record.serialize());

        Ok(MutationResult::Mutated)
    }
}

impl Named for TestLangMutator {
    fn name(&self) -> &Cow<'static, str> {
        static NAME: Cow<'static, str> = Cow::Borrowed("TestLangMutator");
        &NAME
    }
}

#[derive(Debug)]
struct ParsedRecord {
    name: String,
    size: usize,
    fields: Vec<(String, ParsedField)>,
}

impl ParsedRecord {
    fn parse(blob: &[u8], grammar: &Grammar) -> Result<Self, Error> {
        let records = grammar.records();

        let root_record = records
            .get("INPUT")
            .ok_or(Error::unsupported("INPUT not found"))?;

        Self::parse_record(&blob, &records, root_record)
    }

    fn parse_record(
        blob: &[u8],
        grammar: &HashMap<String, &Record>,
        record: &Record,
    ) -> Result<Self, Error> {
        let mut field_values = vec![];
        let mut i = 0;

        // check if record is union type
        if matches!(record.ty, RecordType::Union) {
            for field in &record.fields {
                let sub_record = grammar
                    .get(&field.name)
                    .ok_or(Error::unsupported("invalid field"))?;
                if let Ok(sub_record) = Self::parse_record(&blob, grammar, sub_record) {
                    // TODO: double check
                    return Ok(ParsedRecord {
                        name: record.name.clone(),
                        size: sub_record.size,
                        fields: vec![(
                            sub_record.name.clone(),
                            ParsedField::Record {
                                name: sub_record.name.clone(),
                                size: sub_record.size,
                                record: sub_record,
                            },
                        )],
                    });
                }
            }
            return Err(Error::unsupported("invalid union"));
        }

        for field in &record.fields {
            let value = match field.ty {
                FieldType::Normal => {
                    let field_size = field
                        .attributes
                        .get("size")
                        .ok_or(Error::unsupported("invalid size"))?;

                    let size = match field_size {
                        Attribute::Number(value) => *value as usize,
                        Attribute::Word(_) => return Err(Error::unsupported("invalid size")),
                        Attribute::Reference(field) => {
                            let value = field_values
                                .iter()
                                .find(|(name, _)| name == field)
                                .ok_or(Error::unsupported("invalid reference"))?;
                            match &value.1 {
                                ParsedField::Normal { size, value, .. } => {
                                    bytes_to_integer(value, *size)? as usize
                                }
                                _ => return Err(Error::unsupported("invalid reference")),
                            }
                        }
                    };

                    if size > blob.len() - i {
                        return Err(Error::unsupported("invalid size"));
                    }

                    let value = Vec::from(&blob[i..i + size]);
                    i += size;

                    let field_value = field
                        .attributes
                        .get("value");
                    if let Some(value_attr) = field_value {
                        let expected_value = match value_attr {
                            Attribute::Number(num) => value_to_bytes(*num as u128, size)?,
                            Attribute::Word(word) => {
                                let mut result = Vec::from(word.as_bytes());
                                if result.len() < size {
                                    result.resize(size, 0);
                                }
                                result
                            }
                            Attribute::Reference(_) => {
                                return Err(Error::unsupported("invalid reference"))
                            }
                        };

                        if value != expected_value {
                            return Err(Error::unsupported("invalid value"));
                        }
                    }

                    ParsedField::Normal {
                        name: field.name.clone(),
                        size,
                        value,
                    }
                }
                FieldType::Array => {
                    let count = if let Some(size) = field.attributes.get("size") {
                        match size {
                            Attribute::Number(value) => *value as usize,
                            Attribute::Word(_) => return Err(Error::unsupported("invalid size")),
                            Attribute::Reference(field) => {
                                let value = field_values
                                    .iter()
                                    .find(|(name, _)| name == field)
                                    .ok_or(Error::unsupported("invalid reference"))?;
                                match &value.1 {
                                    ParsedField::Normal { size, value, .. } => {
                                        bytes_to_integer(value, *size)? as usize
                                    }
                                    _ => return Err(Error::unsupported("invalid reference")),
                                }
                            }
                        }
                    } else {
                        usize::max_value()
                    };

                    let record = grammar
                        .get(&field.name)
                        .ok_or(Error::unsupported("invalid field"))?;
                    let mut j = 0;
                    let mut total_size = 0;

                    let mut records = vec![];
                    while i < blob.len() && j < count {
                        if let Ok(record) = Self::parse_record(&blob[i..], grammar, record) {
                            i += record.size;
                            total_size += record.size;
                            records.push(record);
                            j += 1
                        } else {
                            break;
                        }
                    }

                    ParsedField::Array {
                        name: field.name.clone(),
                        size: total_size,
                        records,
                    }
                }
                FieldType::Record => {
                    let record = grammar
                        .get(&field.name)
                        .ok_or(Error::unsupported("invalid field"))?;
                    let record = Self::parse_record(&blob[i..], grammar, record)?;
                    i += record.size;

                    ParsedField::Record {
                        name: field.name.clone(),
                        size: record.size,
                        record,
                    }
                }
            };

            field_values.push((field.name.clone(), value));
        }

        Ok(ParsedRecord {
            name: record.name.clone(),
            size: i,
            fields: field_values,
        })
    }

    fn height_map(&self) -> Vec<usize> {
        let mut result = vec![];

        fn height_map_explore(result: &mut Vec<usize>, node: &ParsedRecord, depth: usize) {
            if depth >= result.len() {
                result.push(1)
            } else {
                result[depth] += 1;
            }

            for (_, field) in &node.fields {
                match field {
                    ParsedField::Normal { .. } => {}
                    ParsedField::Record { record, .. } => {
                        height_map_explore(result, record, depth + 1)
                    }
                    ParsedField::Array { records, .. } => {
                        for record in records {
                            height_map_explore(result, record, depth + 1)
                        }
                    }
                }
            }
        }

        height_map_explore(&mut result, self, 0);
        result
    }

    fn find_record(&mut self, depth: usize, mut index: usize) -> Option<&mut ParsedRecord> {
        fn find_record_explore<'a>(
            node: &'a mut ParsedRecord,
            depth: usize,
            index: &mut usize,
        ) -> Option<&'a mut ParsedRecord> {
            if depth == 0 {
                if *index == 0 {
                    return Some(node);
                } else {
                    *index -= 1;
                }
            }

            for (_, field) in node.fields.iter_mut() {
                match field {
                    ParsedField::Normal { .. } => {}
                    ParsedField::Record { record, .. } => {
                        if let Some(result) = find_record_explore(record, depth - 1, index) {
                            return Some(result);
                        }
                    }
                    ParsedField::Array { records, .. } => {
                        for record in records {
                            if let Some(result) = find_record_explore(record, depth - 1, index) {
                                return Some(result);
                            }
                        }
                    }
                }
            }

            None
        }

        find_record_explore(self, depth, &mut index)
    }

    fn serialize(&self) -> Vec<u8> {
        let mut result = vec![];

        fn serialize_explore(result: &mut Vec<u8>, node: &ParsedRecord) {
            for (_, field) in &node.fields {
                match field {
                    ParsedField::Normal { value, .. } => {
                        result.extend_from_slice(value);
                    }
                    ParsedField::Record { record, .. } => {
                        serialize_explore(result, record);
                    }
                    ParsedField::Array { records, .. } => {
                        for record in records {
                            serialize_explore(result, record);
                        }
                    }
                }
            }
        }

        serialize_explore(&mut result, self);
        result
    }
}

#[derive(Debug)]
enum ParsedField {
    Normal {
        name: String,
        size: usize,
        value: Vec<u8>,
    },
    Record {
        name: String,
        size: usize,
        record: ParsedRecord,
    },
    Array {
        name: String,
        size: usize,
        records: Vec<ParsedRecord>,
    },
}

fn bytes_to_integer(bytes: &[u8], size: usize) -> Result<u128, Error> {
    Ok(match size {
        1 => bytes[0] as u128,
        2 => u16::from_ne_bytes([bytes[0], bytes[1]]) as u128,
        4 => u32::from_ne_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]) as u128,
        8 => u64::from_ne_bytes([
            bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7],
        ]) as u128,
        16 => u128::from_ne_bytes([
            bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6], bytes[7],
            bytes[8], bytes[9], bytes[10], bytes[11], bytes[12], bytes[13], bytes[14], bytes[15],
        ]),
        _ => return Err(Error::unsupported("invalid size")),
    })
}

macro_rules! mutate_test_case {
    ($name:ident, $input:expr) => {
        #[test]
        fn $name() {
            use libafl::prelude::*;

            let grammar = Grammar::parse(include_str!($input)).unwrap();

            let records = grammar.records();
            let input_record = records.get("INPUT").unwrap();

            let mut state = NopState::<NopInput>::new();
            state.rand_mut().set_seed(0);
            for _ in 0..5 {
                let g = generate_record(&mut state, input_record, &records).unwrap();
                ParsedRecord::parse(&g, &grammar).unwrap();
            }
        }
    };
}

mutate_test_case!(cadet_00001_2, "../testlangs/CADET-00001-2-ext.txt");
mutate_test_case!(cadet_00001, "../testlangs/CADET-00001.txt");
mutate_test_case!(cromu_00001, "../testlangs/CROMU-00001.txt");
mutate_test_case!(cromu_00003_ext, "../testlangs/CROMU-00003-ext.txt");
mutate_test_case!(cromu_00003, "../testlangs/CROMU-00003.txt");
mutate_test_case!(cromu_00004, "../testlangs/CROMU-00004.txt");
mutate_test_case!(cromu_00005, "../testlangs/CROMU-00005.txt");
mutate_test_case!(cve_2021_38208, "../testlangs/CVE-2021-38208.txt");
mutate_test_case!(cve_2022_0185_ext, "../testlangs/CVE-2022-0185-ext.txt");
mutate_test_case!(cve_2022_0185, "../testlangs/CVE-2022-0185.txt");
mutate_test_case!(cve_2022_0995_2, "../testlangs/CVE-2022-0995-2.txt");
mutate_test_case!(cve_2022_0995, "../testlangs/CVE-2022-0995.txt");
mutate_test_case!(cve_2022_32250_2_ext, "../testlangs/CVE-2022-32250-2-ext.txt");
mutate_test_case!(cve_2022_32250_2, "../testlangs/CVE-2022-32250-2.txt");
mutate_test_case!(cve_2022_32250_ext, "../testlangs/CVE-2022-32250-ext.txt");
mutate_test_case!(cve_2022_32250, "../testlangs/CVE-2022-32250.txt");
mutate_test_case!(cve_2023_2513_ext, "../testlangs/CVE-2023-2513-ext.txt");
mutate_test_case!(cve_2023_2513, "../testlangs/CVE-2023-2513.txt");
mutate_test_case!(good_example, "../testlangs/_good-example.txt");
mutate_test_case!(kprca_00001_ext, "../testlangs/KPRCA-00001-ext.txt");
mutate_test_case!(kprca_00001, "../testlangs/KPRCA-00001.txt");
mutate_test_case!(linux_test_harness, "../testlangs/linux_test_harness.txt");
mutate_test_case!(nrfin_00001, "../testlangs/NRFIN-00001.txt");
mutate_test_case!(userspace_1, "../testlangs/userspace-1.txt");
