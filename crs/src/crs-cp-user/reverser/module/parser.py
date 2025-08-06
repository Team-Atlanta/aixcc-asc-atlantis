#from .test_lang import Test

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from lark import Lark, Transformer, Token
from zss import simple_distance

l = Lark(open(Path(__file__).parent / 'grammar-ext.lark').read())
from .tokens import ALLOWED_TYPES, CNT, INPUT, GLOBALS
from . import test_lang as tl

# keep -1 as "not found"
GLOBAL_IDX_START = -2
UNSET_REFERENCE = -1

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

class AtValueType(Enum):
    NUMBER = 0
    STRING = 1
    INRANGE = 2
    EXRANGE = 3
    GROUP = 4

@dataclass
class AtValue:
    ty: AtValueType
    values: List[str | int]
    ref: int = UNSET_REFERENCE

    def update_refs(self, globals_, fields):
        for val in self.values:
            if isinstance(val, str):
                # try to find in field
                try:
                    idx = [f.name for f in fields].index(val)
                    if fields[idx].ty == FieldType.NORMAL:
                        self.ref = idx
                        continue
                except:
                    pass
                if globals_:
                    try:
                        idx = [f.name for f in globals_.fields].index(val)
                        if globals_.fields[idx].ty == FieldType.NORMAL:
                            self.ref = GLOBAL_IDX_START - idx
                            continue
                    except:
                        pass
                raise AttributeError(f'Attribute value {val} does not reference properly')
    
    def __str__(self):
        values = [str(x) for x in self.values]
        if not self.values:
            return ''
        if self.ty == AtValueType.STRING or self.ty == AtValueType.NUMBER:
            return str(values[0])
        if self.ty == AtValueType.INRANGE:
            return '..='.join(values[:2])
        if self.ty == AtValueType.EXRANGE:
            return '..'.join(values[:2])
        if self.ty == AtValueType.GROUP:
            return ' | '.join(values)
        return ''

# TODO: annotate with start and end so we can have better error messages
class FieldType(Enum):
  NORMAL = 0
  RECORD = 1
  ARRAY = 2

@dataclass
class Field:
    name: str
    ty: FieldType
    attributes: Dict[str, AtValue]

    def update_refs(self, globals_, fields):
        for (k, atv) in self.attributes.items():
            if k == 'type':
                if len(atv.values) != 1 or atv.values[0] not in ALLOWED_TYPES:
                    raise AttributeError(f'attribute {k} of field {self.name} has unknown type! acceptable types: {str(ALLOWED_TYPES)}')
            else:
                atv.update_refs(globals_, fields)
    
    def to_tree(self, i: Optional[int], records: Dict[str, object], fields: List[object]) -> TreeNode:
        attributes = ['_type:field'] + ([f'_order:{i}'] if i else [])
        for key, atv in self.attributes.items():
            if len(atv.values) == 1 and isinstance(atv.values[0], int):
                attributes.append(f'{key}:{atv.values[0]}')
            elif len(atv.values) == 1 and atv.ref != UNSET_REFERENCE:
                attributes.append(f'{key}:ref_{atv.ref}')
            else:
                attributes.append(f'{key}:{str(atv)}')

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

    def update_refs(self, globals_):
        for field in self.fields:
            field.update_refs(globals_, self.fields)

    def flatten(self, records: Dict[str, object], flat_records: Dict[str, object]) -> object:
        if self.ty == RecordType.UNION:
            return self
        
        flattened_arrays_fields = []
        for field in self.fields:
            if field.ty == FieldType.ARRAY and CNT in field.attributes and field.attributes[CNT].ty == AtValueType.NUMBER:
                new_attributes = field.attributes.copy()
                del new_attributes[CNT]
                array_size = field.attributes[CNT].values[0] # should be int...
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
    records: Dict[str, Record]
    input_record: Record | None = None
    globals_record: Record | None = None

    def __post_init__(self):
        if INPUT not in self.records:
            raise "INPUT record not found!"
        self.input_record = self.records[INPUT]
        if GLOBALS in self.records:
            self.globals_record = self.records[GLOBALS]
        for (name, record) in self.records.items():
            if name == GLOBALS:
                continue
            record.update_refs(self.globals_record)
    
    def to_tree(self) -> TreeNode:
        return self.input_record.to_tree(self.records)

    def flatten(self) -> object:
        return TestingLanguage(list(record.flatten(records) for record in self.records.values()))
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, TestingLanguage):
            return self.to_tree() == value.to_tree()
        return False

    def get_classic(self) -> tl.TestLang:
        classic = tl.TestLang()
        for (name, record) in self.records.items():
            classic_record = tl.Record(name)
            classic_record.update_type(int(record.ty.value))
            for field in record.fields:
                classic_field = tl.Field(
                    field.name,
                    int(field.ty.value),
                    dict([(k, str(v)) for (k, v) in field.attributes.items()])
                )
                classic_record.add_field(classic_field)
            classic.add_record(classic_record)
        return classic

class TreeToTestingLanguage(Transformer):
    start = lambda _, n : TestingLanguage(dict([(r.name, r) for r in n]))

    seq = lambda _, n : Record(n[0], RecordType.SEQ, n[1:])
    union = lambda _, n : Record(n[0], RecordType.UNION, n[1:])

    normal = lambda _, n : Field(n[0], FieldType.NORMAL, n[1])
    array = lambda _, n : Field(n[0], FieldType.ARRAY, {CNT: n[1]}) # not sure how array size is meant to be encoded
    reference = lambda _, n : Field(n[0], FieldType.RECORD, {})
    field = lambda _, n: n[0]

    global_ = lambda _, n : Field(n[0], FieldType.NORMAL, dict(n[1:]))
    globals_ = lambda _, n : Record("GLOBALS", RecordType.SEQ, n)

    attribute_list = lambda _, a : dict(a)
    # attribute = lambda _, a : (a[0], a[1])
    attribute = lambda _, a : a[0]
    size_attribute = lambda _, a : (str(a[0]), a[1])
    value_attribute = lambda _, a : (str(a[0]), a[1])
    type_attribute = lambda _, a : (str(a[0]), AtValue(AtValueType.STRING, [str(a[1])]))
    terminator_attribute = lambda _, a : (a[0], AtValue(AtValueType.NUMBER, [int(a[1])]))
    literal = lambda _, n: n[0]
    CNAME = lambda _, n: str(n)

    inrange = lambda _, t: AtValue(AtValueType.INRANGE, t)
    exrange = lambda _, t: AtValue(AtValueType.EXRANGE, t)
    group = lambda _, t: AtValue(AtValueType.GROUP, t)

    def atvalue(self, s):
        s = s[0]
        if isinstance(s, int):
            return AtValue(AtValueType.NUMBER, [s])
        if isinstance(s, str):
            return AtValue(AtValueType.STRING, [s])
        return s

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
    try:
        test_lang = TreeToTestingLanguage().transform(tree)
    except Exception as e:
        return None, e
    return test_lang, None

# TODO Check that grammar is tree w/ root INPUT
#      Assuming grammar is tree, loosen reference scoping checks
# TODO check that INPUT and GLOBAL is standalone, not referenced by anything
# TODO check reference for global fields
# TODO make sure GLOBAL only has normals
def check_semantics(language: TestingLanguage):
    names = language.records.keys()
    
    for record in language.records.values():
        field_names = set(field.name for field in record.fields)

        # make sure duplicate field names are not NORMAL's
        normal_names = [field.name for field in record.fields if field.ty == FieldType.NORMAL]
        for i in range(len(normal_names) - 1):
            for j in range(i + 1, len(normal_names)):
                if normal_names[i] == normal_names[j]:
                    return f'duplicate primitive fields "{normal_names[i]}", in record "{record.name}"'

        # make sure normals do not share same name as records
        for nname in normal_names:
            if nname in names:
                return f'normal field "{nname}" in record "{record.name}" shares the same name as a record "{nname}"'

        for field in record.fields:
            if field.ty == FieldType.RECORD or field.ty == FieldType.ARRAY:
                if field.name not in names:
                    return f'unknown record reference "{field.name}" in record "{record.name}"'
            
            # TODO field reference could ref a field from 'parent'. Assuming grammar is tree
            # NOTE This logic is now checked at construction
            # for attribute, atv in field.attributes.items():
            #     if ref and ref not in field_names:
            #         return f'unknown field reference "{ref}" in attribute "{attribute}" of record "{record.name}"'
            #     # Check that field references are not records (i.e. are NORMALS)
            #     if ref and ref in language.records:
            #         return f'field reference "{ref}" is not of the form "{ref}" {{ size: ... }}'
            #     if attribute == 'type':
            #         if s not in ALLOWED_TYPES:
            #             return f'attribute "{attribute}" of field "{field.name}" has unknown type: {s}; acceptable types: {str(ALLOWED_TYPES)}'
                    
    return None

def main():
    from sys import argv
    test_langs = []
    for arg in argv[1:]:
        data = open(arg).read()
        test_lang, err = read_into_test_lang(data)
        print(arg)
        print(test_lang)
        print(err)
        if err:
            continue
        classic = test_lang.get_classic()
        print(classic)
        print(check_semantics(test_lang))
        print(test_lang.to_tree())
        test_langs.append(test_lang)
    if len(argv) == 3:
        print(f'Is equal? {test_langs[0] == test_langs[1]}\nDistance {test_langs[0].to_tree().distance(test_langs[1].to_tree())}')

if __name__ == '__main__':
    main()
