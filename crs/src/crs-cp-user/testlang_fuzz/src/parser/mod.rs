use itertools::Itertools;
use std::collections::{HashMap, HashSet};

use pyo3::{
    prelude::*,
    types::{PyDict, PyInt, PyList, PyString},
};

#[derive(Debug)]
pub struct Grammar(pub Vec<Record>);

impl Grammar {
    pub fn records(&self) -> HashMap<String, &Record> {
        HashMap::from_iter(self.0.iter().map(|record| (record.name.clone(), record)))
    }

    pub fn parse(s: &str) -> Result<Grammar, Box<dyn std::error::Error>> {
        Python::with_gil(|py| -> Result<Grammar, Box<dyn std::error::Error>> {
            let module =
                PyModule::from_code_bound(py, include_str!("parser.py"), "parser.py", "parser")?;
            let read_into_test_lang = module.getattr("read_into_test_lang")?;
            let result = read_into_test_lang.call1((s,))?;
            let language = result.get_item(0)?;

            let records = language
                .getattr("records")?
                .downcast_into::<PyList>()
                .unwrap()
                .into_iter()
                .map(|field| Self::convert_record(&module, field))
                .try_collect()?;

            Ok(Grammar(records))
        })
    }

    fn convert_record(
        module: &Bound<PyModule>,
        record: Bound<PyAny>,
    ) -> Result<Record, Box<dyn std::error::Error>> {
        let seq = module.getattr("RecordType")?.getattr("SEQ")?;
        let name: String = record
            .getattr("name")?
            .downcast_into::<PyString>()
            .unwrap()
            .extract()?;
        let ty = record.getattr("ty")?;
        let ty = if ty.eq(seq)? {
            RecordType::Sequential
        } else {
            RecordType::Union
        };

        let fields: Vec<Field> = record
            .getattr("fields")?
            .downcast_into::<PyList>()
            .unwrap()
            .into_iter()
            .map(|record| Self::convert_field(module, record))
            .try_collect()?;

        Ok(Record { name, ty, fields })
    }

    fn convert_field(
        module: &Bound<PyModule>,
        field: Bound<PyAny>,
    ) -> Result<Field, Box<dyn std::error::Error>> {
        let normal = module.getattr("FieldType")?.getattr("NORMAL")?;
        let array = module.getattr("FieldType")?.getattr("ARRAY")?;
        let name: String = field
            .getattr("name")?
            .downcast_into::<PyString>()
            .unwrap()
            .extract()?;
        let ty = field.getattr("ty")?;
        let attributes = field
            .getattr("attributes")?
            .downcast_into::<PyDict>()
            .unwrap();
        let attributes = Self::convert_attributes(attributes)?;
        let ty = if ty.eq(normal)? {
            FieldType::Normal
        } else if ty.eq(array)? {
            FieldType::Array
        } else {
            FieldType::Record
        };

        Ok(Field {
            name,
            ty,
            attributes,
        })
    }

    fn convert_attributes(
        dict: Bound<PyDict>,
    ) -> Result<HashMap<String, Attribute>, Box<dyn std::error::Error>> {
        dict.into_iter()
            .map(
                |(name, attr)| -> Result<(String, Attribute), Box<dyn std::error::Error>> {
                    let name: String = name.downcast_into::<PyString>().unwrap().extract()?;
                    if !attr.get_item(0)?.is_none() {
                        let num: i128 = attr
                            .get_item(0)?
                            .downcast_into::<PyInt>()
                            .unwrap()
                            .extract()?;
                        Ok((name, Attribute::Number(num)))
                    } else if !attr.get_item(1)?.is_none() {
                        let word: String = attr
                            .get_item(1)?
                            .downcast_into::<PyString>()
                            .unwrap()
                            .extract()?;
                        Ok((name, Attribute::Word(word)))
                    } else {
                        let reference: String = attr
                            .get_item(2)?
                            .downcast_into::<PyString>()
                            .unwrap()
                            .extract()?;
                        Ok((name, Attribute::Reference(reference)))
                    }
                },
            )
            .try_collect()
    }


}

#[derive(Debug)]
pub struct Record {
    pub name: String,
    pub ty: RecordType,
    pub fields: Vec<Field>,
}

impl Record {
    pub fn independent_fields(&self) -> Vec<(usize, &Field)> {
        let mut independent_fields: HashSet<String> =
            HashSet::from_iter(self.fields.iter().map(|field| field.name.clone()));

        for field in &self.fields {
            if let Some(value) = field.attributes.get("value") {
              if matches!(value, Attribute::Reference(_)) {
                independent_fields.remove(&field.name);
              }
            }

            if let Some(size) = field.attributes.get("size") {
                match size {
                    Attribute::Reference(name) => {
                        independent_fields.remove(name);
                    }
                    _ => {}
                }
            }

            if let Some(size) = field.attributes.get("array_size") {
                match size {
                    Attribute::Reference(name) => {
                        independent_fields.remove(name);
                    }
                    _ => {}
                }
            }
        }

        let mut result = vec![];
        for (i, field) in self.fields.iter().enumerate() {
            if independent_fields.contains(&field.name) {
                result.push((i, field));
            }
        }

        result
    }
}

#[derive(Debug)]
pub enum RecordType {
    Sequential,
    Union,
}

#[derive(Debug)]
pub struct Field {
    pub name: String,
    pub ty: FieldType,
    pub attributes: HashMap<String, Attribute>,
}

#[derive(Debug)]
pub enum FieldType {
    Normal,
    Array,
    Record,
}

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Attribute {
    Number(i128),
    Word(String),
    Reference(String),
}

macro_rules! parse_test_case {
    ($name:ident, $input:expr) => {
        #[test]
        fn $name() {
            let grammar = Grammar::parse(include_str!($input)).unwrap();
        }
    };
}

parse_test_case!(cadet_00001_2, "../testlangs/CADET-00001-2-ext.txt");
parse_test_case!(cadet_00001, "../testlangs/CADET-00001.txt");
parse_test_case!(cromu_00001, "../testlangs/CROMU-00001.txt");
parse_test_case!(cromu_00003_ext, "../testlangs/CROMU-00003-ext.txt");
parse_test_case!(cromu_00003, "../testlangs/CROMU-00003.txt");
parse_test_case!(cromu_00004, "../testlangs/CROMU-00004.txt");
parse_test_case!(cromu_00005, "../testlangs/CROMU-00005.txt");
parse_test_case!(cve_2021_38208, "../testlangs/CVE-2021-38208.txt");
parse_test_case!(cve_2022_0185_ext, "../testlangs/CVE-2022-0185-ext.txt");
parse_test_case!(cve_2022_0185, "../testlangs/CVE-2022-0185.txt");
parse_test_case!(cve_2022_0995_2, "../testlangs/CVE-2022-0995-2.txt");
parse_test_case!(cve_2022_0995, "../testlangs/CVE-2022-0995.txt");
parse_test_case!(cve_2022_32250_2_ext, "../testlangs/CVE-2022-32250-2-ext.txt");
parse_test_case!(cve_2022_32250_2, "../testlangs/CVE-2022-32250-2.txt");
parse_test_case!(cve_2022_32250_ext, "../testlangs/CVE-2022-32250-ext.txt");
parse_test_case!(cve_2022_32250, "../testlangs/CVE-2022-32250.txt");
parse_test_case!(cve_2023_2513_ext, "../testlangs/CVE-2023-2513-ext.txt");
parse_test_case!(cve_2023_2513, "../testlangs/CVE-2023-2513.txt");
parse_test_case!(good_example, "../testlangs/_good-example.txt");
parse_test_case!(kprca_00001_ext, "../testlangs/KPRCA-00001-ext.txt");
parse_test_case!(kprca_00001, "../testlangs/KPRCA-00001.txt");
parse_test_case!(linux_test_harness, "../testlangs/linux_test_harness.txt");
parse_test_case!(nrfin_00001, "../testlangs/NRFIN-00001.txt");
parse_test_case!(userspace_1, "../testlangs/userspace-1.txt");