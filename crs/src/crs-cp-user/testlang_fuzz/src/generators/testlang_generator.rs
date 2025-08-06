use std::collections::HashMap;

use libafl::{generators::Generator, inputs::BytesInput, state::HasRand, Error};
use libafl_bolts::rands::Rand;
use crate::parser::RecordType;

use crate::parser::{Attribute, FieldType, Grammar, Record};

pub struct TestlangGenerator(Grammar);

const MAX_ARRAY_SIZE: usize = 5;


// TODO: add support for standard Generators
// TODO: implement value of a field is a field


impl<S> Generator<BytesInput, S> for TestlangGenerator
where
    S: HasRand,
{
    fn generate(&mut self, state: &mut S) -> Result<BytesInput, Error> {
        let records = self.0.records();

        let root_record = records
            .get("INPUT")
            .ok_or(Error::unsupported("INPUT not found"))?;

        Ok(BytesInput::new(generate_record(
            state,
            root_record,
            &records,
        )?))
    }
}

pub fn generate_record<S: HasRand>(
    state: &mut S,
    record: &Record,
    records: &HashMap<String, &Record>,
) -> Result<Vec<u8>, Error> {
    if matches!(record.ty, RecordType::Union) {
        println!("NAME {:?}", record);
        let options_len = record.fields.len();
        let i = state.rand_mut().below(options_len);
        let field = &record.fields[i];
        let sub_record = records
            .get(&field.name)
            .ok_or(Error::unsupported("FIELD not found"))?;
        return generate_record(state, sub_record, records);
    }

    let mut fields: Vec<Vec<u8>> = vec![vec![]; record.fields.len()];

    for (i, field) in record.independent_fields() {
        match field.ty {
            FieldType::Normal => {
                let size = field
                    .attributes
                    .get("size")
                    .ok_or(Error::unsupported("invalid size"))?;
                
                if let Some(value) = field.attributes.get("value") {
                    let size = if let Attribute::Number(size) = size {
                        *size as usize
                    } else {
                        0
                    };

                    let buffer = match value {
                        Attribute::Number(num) => value_to_bytes(*num as u128, size)?,
                        Attribute::Word(word) => {
                            let mut result = Vec::from(word.as_bytes());
                            if result.len() < size {
                                result.resize(size, 0);
                            }
                            result
                        }
                        Attribute::Reference(_) => {
                            return Err(Error::unsupported("impossible independent field"))
                        }
                    };

                    fields[i] = buffer;
                } else {
                    let is_string = field
                        .attributes
                        .get("type")
                        .map_or(false, |ty| ty == &Attribute::Word("string".to_string()));

                    let size = if let Attribute::Number(size) = size {
                        *size as usize
                    } else {
                        // allow longer
                        state.rand_mut().below(256)
                    };

                    // TODO: how to pick size?
                    // TODO: should string be limited to printables?
                    // TODO: don't use subsize if strictly equal size?

                    let mut buffer = vec![0; size];
                    let sub_size = state
                        .rand_mut()
                        .between(0, if is_string && size > 0 { size - 1 } else { size });
                    for i in 0..sub_size {
                        buffer[i] = state.rand_mut().below(256) as u8;
                    }

                    fields[i] = buffer;
                }
            }
            FieldType::Array => {
                let sub_record = records
                    .get(&field.name)
                    .ok_or(Error::unsupported("INPUT not found"))?;

                let array_size = state.rand_mut().between(0, MAX_ARRAY_SIZE);

                if let Some(size_field) = field.attributes.get("array_size") {
                    if let Attribute::Reference(size_field) = size_field {
                        let (j, size_field) = record
                            .fields
                            .iter()
                            .enumerate()
                            .find(|(_, field)| field.name == *size_field)
                            .ok_or(Error::unsupported("size field not found"))?;

                        // TODO: is number attribute limited to u128?

                        let size_field_size = size_field
                            .attributes
                            .get("size")
                            .ok_or(Error::unsupported("size field not found"))
                            .and_then(|size| {
                                if let Attribute::Number(size) = size {
                                    Ok(size)
                                } else {
                                    Err(Error::unsupported("size field not found"))
                                }
                            })?;

                        let size_field_value =
                            value_to_bytes(array_size as u128, *size_field_size as usize)?;
                        fields[j] = size_field_value;
                    }
                }

                let mut collected = vec![];
                for _ in 0..array_size {
                    let sub_record = generate_record(state, sub_record, records)?;
                    collected.extend_from_slice(&sub_record);
                }

                fields[i] = collected;
            }
            FieldType::Record => {
                let sub_record = records
                    .get(&field.name)
                    .ok_or(Error::unsupported("INPUT not found"))?;
                let sub_record = generate_record(state, sub_record, records)?;

                fields[i] = sub_record;
            }
        }
    }

    Ok(fields.concat())
}

pub fn value_to_bytes(value: u128, size: usize) -> Result<Vec<u8>, Error> {
    match size {
        1 => Ok(Vec::from((value as u8).to_ne_bytes())),
        2 => Ok(Vec::from((value as u16).to_ne_bytes())),
        4 => Ok(Vec::from((value as u32).to_ne_bytes())),
        8 => Ok(Vec::from((value as u64).to_ne_bytes())),
        16 => Ok(Vec::from(value.to_ne_bytes())),
        _ => return Err(Error::unsupported("invalid size")),
    }
}

macro_rules! generate_test_case {
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
                generate_record(&mut state, input_record, &records).unwrap();
            }
        }
    };
}

generate_test_case!(cadet_00001_2, "../testlangs/CADET-00001-2-ext.txt");
generate_test_case!(cadet_00001, "../testlangs/CADET-00001.txt");
generate_test_case!(cromu_00001, "../testlangs/CROMU-00001.txt");
generate_test_case!(cromu_00003_ext, "../testlangs/CROMU-00003-ext.txt");
generate_test_case!(cromu_00003, "../testlangs/CROMU-00003.txt");
generate_test_case!(cromu_00004, "../testlangs/CROMU-00004.txt");
generate_test_case!(cromu_00005, "../testlangs/CROMU-00005.txt");
generate_test_case!(cve_2021_38208, "../testlangs/CVE-2021-38208.txt");
generate_test_case!(cve_2022_0185_ext, "../testlangs/CVE-2022-0185-ext.txt");
generate_test_case!(cve_2022_0185, "../testlangs/CVE-2022-0185.txt");
generate_test_case!(cve_2022_0995_2, "../testlangs/CVE-2022-0995-2.txt");
generate_test_case!(cve_2022_0995, "../testlangs/CVE-2022-0995.txt");
generate_test_case!(cve_2022_32250_2_ext, "../testlangs/CVE-2022-32250-2-ext.txt");
generate_test_case!(cve_2022_32250_2, "../testlangs/CVE-2022-32250-2.txt");
generate_test_case!(cve_2022_32250_ext, "../testlangs/CVE-2022-32250-ext.txt");
generate_test_case!(cve_2022_32250, "../testlangs/CVE-2022-32250.txt");
generate_test_case!(cve_2023_2513_ext, "../testlangs/CVE-2023-2513-ext.txt");
generate_test_case!(cve_2023_2513, "../testlangs/CVE-2023-2513.txt");
generate_test_case!(good_example, "../testlangs/_good-example.txt");
generate_test_case!(kprca_00001_ext, "../testlangs/KPRCA-00001-ext.txt");
generate_test_case!(kprca_00001, "../testlangs/KPRCA-00001.txt");
generate_test_case!(linux_test_harness, "../testlangs/linux_test_harness.txt");
generate_test_case!(nrfin_00001, "../testlangs/NRFIN-00001.txt");
generate_test_case!(userspace_1, "../testlangs/userspace-1.txt");
