#from .test_lang import Test

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from lark import Lark, Transformer, Token
from zss import simple_distance

l = Lark(open(Path(__file__).parent / 'grammar.lark').read())
from .tokens import ALLOWED_TYPES


@dataclass
class TreeNode:
    attributes: List[str]
    children: List[object]

    def __hash__(self):
        return hash((tuple(self.attributes), tuple(hash(child) for child in self.children)))

    def __eq__(self, other):
        if set(self.attributes) != set(other.attributes):
            return False
        
        if len(self.children) != len(other.children):
            return False

        for a, b in zip(self.children, other.children):
            if a != b:
                return False
        
        return True

    def get_children(self):
        return self.children
    
    def get_label(self):
        return ';'.join(str(hash(attribute)) for attribute in self.attributes)

    @staticmethod
    def get_label_difference(one, two):
        one, two = set(one.split(';')), set(two.split(';'))
        return len(one ^ two)
    
    def distance(self, other):
        return simple_distance(self, other, TreeNode.get_children, TreeNode.get_label, TreeNode.get_label_difference)


# TODO: annotate with start and end so we can have better error messages
class FieldType(Enum):
  NORMAL = 0
  ARRAY = 1
  RECORD = 2

@dataclass
class Field:
    name: str
    ty: FieldType
    attributes: Dict[str, Tuple[int, str, str]]

    def to_tree(self, i: Optional[int], records: Dict[str, object], fields: List[object]) -> TreeNode:
        attributes = ['_type:field'] + ([f'_order:{i}'] if i else [])
        for key, (num, lit, ref) in self.attributes.items():
            if num:
                attributes.append(f'{key}:{num}')
            if lit:
                attributes.append(f'{key}:{lit}')
            if ref:
                index = next(i for i, field in enumerate(fields) if field.name == ref)
                attributes.append(f'{key}:ref_{index}')

        children = []
        if self.ty != FieldType.NORMAL:
            children.append(records[self.name].to_tree(records))

        return TreeNode(attributes, children)


class RecordType(Enum):
  SEQ = 0
  UNION = 1

@dataclass
class Record:
    name: str
    ty: RecordType
    fields: List[Field]

    def flatten(self, records: Dict[str, object], flat_records: Dict[str, object]) -> object:
        if self.ty == RecordType.UNION:
            return self
        
        flattened_arrays_fields = []
        for field in self.fields:
            (array_size, _, _) = field.attributes.get('array_size', (None, None, None))
            if field.ty == FieldType.ARRAY and array_size:
                new_attributes = field.attributes.copy()
                del new_attributes['array_size']

                for _ in range(array_size):
                    flattened_arrays_fields.append(Field(field.name, FieldType.RECORD, new_attributes))
            else:
                flattened_arrays_fields.append(field)

        flattened_fields = []
        for field in flattened_arrays_fields:
            add_field = True
            if field.ty == FieldType.RECORD:
                record = records[field.name]
                add_field = record.ty == RecordType.SEQ
            
            if not add_field:
                flattened_fields.append(field)
                continue
                
            if field.name not in flat_records:
                flat_records[field.name] = records[field.name].flatten(records, flat_records)
            
            for sub_field in flat_records[field.name]:
                flattened_fields.append(sub_field)

        return Record(self.name, self.ty, flattened_fields)
          
    def to_tree(self, records: Dict[str, object]) -> TreeNode:
        attributes = ['_type:record']

        children = None
        if self.ty == RecordType.UNION:
            all_children_records = all(child.ty == FieldType.RECORD for child in self.fields)
            if all_children_records:
                child_records = list(records[child.name] for child in self.fields)
                first_field = list(record.fields[0] for record in child_records)
                values = list(field.attributes.get('value') for field in first_field)
                if all(values):
                    children = list(sorted(enumerate(self.fields), key=lambda x : values[x[0]]))
                    children = list(child.to_tree(None, records, self.fields) for _, child in children)

        if children is None:
            children = list(field.to_tree(i, records, self.fields) 
                        for i, field in enumerate(self.fields))
        return TreeNode(attributes, children)

@dataclass
class TestingLanguage:
    records: List[Record]

    def records_dict(self) -> Dict[str, Record]:
        return {record.name:record for record in self.records}

    def to_tree(self) -> TreeNode:
        found = None
        for record in self.records:
            if record.name == 'INPUT':
                found = record
                break
        else:
            found = self.records[0]
        return found.to_tree(self.records_dict())

    def flatten(self) -> object:
        records_dict = self.records_dict()
        return TestingLanguage(list(record.flatten(records_dict) for record in self.records))
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, TestingLanguage):
            return self.to_tree() == value.to_tree()
        return False

class TreeToTestingLanguage(Transformer):
    start = lambda _, n : TestingLanguage(n)

    seq = lambda _, n : Record(n[0], RecordType.SEQ, n[1:])
    union = lambda _, n : Record(n[0], RecordType.UNION, n[1:])

    normal = lambda _, n : Field(n[0].value, FieldType.NORMAL, dict(n[1]))
    array = lambda _, n : Field(n[0].value, FieldType.ARRAY, {'array_size': n[1]}) # not sure how array size is meant to be encoded
    record = lambda _, n : Field(n[0].value, FieldType.RECORD, {})

    attribute_list = lambda _, a : dict(a)
    attribute = lambda _, a : (a[0].value, a[1])

    def literal(self, s):
        s = s[0]
        if isinstance(s, Token):
            return (None, s.value, None) if s.value[0].islower() else (None, None, s.value)
        if isinstance(s, int):
            return (s, None, None)
    
    def number(self, n):
        data = ''.join(c for (c, ) in n)
        return int(data, 16 if any(c in data for c in 'abcdefABCDEF') else 10)


def remove_comments(s) -> str:
    return '\n'.join(l.split('//')[0] for l in s.splitlines()).strip()

def read_into_test_lang(s) -> Tuple[TestingLanguage, str]:
    s = remove_comments(s)
    s = f'{s}\n\n'
    try:
        tree = l.parse(s)
    except Exception as e:
        #print('found error', e)
        return None, e
    return TreeToTestingLanguage().transform(tree), None

# TODO Check that grammar is tree w/ root INPUT
#      Assuming grammar is tree, loosen reference scoping checks
def check_semantics(language: TestingLanguage):
    names = set(record.name for record in language.records)
    
    for record in language.records:
        field_names = set(field.name for field in record.fields)

        # make sure duplicate field names are not NORMAL's
        normal_names = [field.name for field in record.fields if field.ty == FieldType.NORMAL]
        for i in range(len(normal_names) - 1):
            for j in range(i + 1, len(normal_names)):
                if normal_names[i] == normal_names[j]:
                    return f'duplicate primitive fields "{normal_names[i]}", in record "{record.name}"'

        for field in record.fields:
            if field.ty == FieldType.RECORD or field.ty == FieldType.ARRAY:
                if field.name not in names:
                    return f'unknown record reference "{field.name}" in record "{record.name}"'
            
            # TODO field reference could ref a field from 'parent'. Assuming grammar is tree
            for attribute, (_, s, ref) in field.attributes.items():
                if ref and ref not in field_names:
                    return f'unknown field reference "{ref}" in attribute "{attribute}" of record "{record.name}"'
                # Check that field references are not records (i.e. are NORMALS)
                if ref and ref in [rec.name  for rec in language.records]:
                    return f'field reference "{ref}" is not of the form "{ref}" {{ size: ... }}'
                
                if attribute == 'type':
                    if s not in ALLOWED_TYPES:
                        return f'attribute "{attribute}" of field "{field.name}" has unknown type: {s}; acceptable types: {str(ALLOWED_TYPES)}'
                    
    return None

def main():
    from sys import argv
    test_langs = []
    for arg in argv[1:]:
        data = open(arg).read()
        test_lang, err = read_into_test_lang(data)
        print(arg, err, check_semantics(test_lang))
        print(test_lang.to_tree())
        test_langs.append(test_lang)
    if len(argv) == 3:
        print(f'Is equal? {test_langs[0] == test_langs[1]}\nDistance {test_langs[0].to_tree().distance(test_langs[1].to_tree())}')

if __name__ == '__main__':
    main()
