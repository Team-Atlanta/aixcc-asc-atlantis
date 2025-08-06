from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from lark import Lark, Transformer, Token

grammar = """
start: (record "\\n"*)*

record: CNAME "::=" field+                -> seq
      | CNAME "::=" field ("|" field)*    -> union

field: CNAME "{" attribute_list "}" "\\n"  -> normal
     | CNAME "[" literal "]" "\\n"         -> array
     | CNAME "\\n"                         -> record

attribute_list: [attribute ("," attribute)*]
attribute: CNAME ":" literal

literal: number | CNAME
number: ["+" | "-"] ["0x"] (HEXDIGIT)+

%import common.CNAME
%import common.HEXDIGIT
%ignore " "
"""
l = Lark(grammar)

@dataclass
class TreeNode:
    attributes: List[str]
    children: List[object]
    

class FieldType(Enum):
  NORMAL = 0
  ARRAY = 1
  RECORD = 2

@dataclass
class Field:
    name: str
    ty: FieldType
    attributes: Dict[str, Tuple[int, str, str]]

class RecordType(Enum):
  SEQ = 0
  UNION = 1

@dataclass
class Record:
    name: str
    ty: RecordType
    fields: List[Field]

@dataclass
class TestingLanguage:
    records: List[Record]

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
