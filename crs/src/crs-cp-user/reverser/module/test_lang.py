import sys
from typing import Tuple, Dict, List, Union
from collections import OrderedDict
from .tokens import *

class Field:
    Normal = 0
    Record = 1
    Array = 2
    def __init__(self, name, ty: int, attrs: Dict[str, Union[str, int, List[str]]] = {}):
        self.name = name
        self.type = ty
        self.attrs = attrs
        self.check_attrs()

    def check_attrs(self):
        if self.type == Field.Normal:
            # FIXME for now disable this check, want to enforce it on non-globals
            # if SIZE not in self.attrs:
            #     if TYPE not in self.attrs or self.attrs[TYPE] not in ALLOWED_TYPES:
            #         parse_error("Normal field must have size attribute")
            for key in self.attrs.keys():
                if key not in NORMAL_ATTRS:
                    parse_error(f"Normal field cannot have {key} attribute")
                # if isinstance(self.attrs[key], list) and key != VALUE:
                #     parse_error(f"Normal field with list of values must be {VALUE} attribute, instead found {self.attrs[key]}")
                # if not isinstance(self.attrs[key], list) and not isinstance(self.attrs[key], int) and key == VALUE:
                #     parse_error(f"Normal field {VALUE} attribute must be list or integer, instead found {self.attrs[key]}")
        elif self.type == Field.Array:
            if CNT in self.attrs and len(self.attrs) == 1: return
            parse_error("Array field must have only CNT attribute")
        elif self.type == Field.Record:
            return
        else:
            parse_error("Field must be one of Normal, Record, and Array")

    def __str__(self):
        if self.type == Field.Normal:
            ret = self.name
            ret += " { "
            fields = []
            for key in sorted(self.attrs.keys()):
                value = self.attrs[key]
                fields.append(f"{key}: {value}")
            ret += ", ".join(fields)
            ret += " }"
            return ret
        elif self.type == Field.Record: return self.name
        elif self.type == Field.Array:
            cnt = self.attrs[CNT]
            return f"{self.name}[{cnt}]"
        
    def __eq__(self, other):
        if type(other) != Field: return False
        if self.name != other.name: return False
        if self.type != other.type: return False
        if self.attrs != other.attrs: return False
        return True

class Record:
    SEQ = 0
    UNION= 1

    def __init__(self, name: str = ""):
        self.name = name
        self.type = None
        self.fields: List[Field] = []

    def add_field(self, field: Field):
        self.fields.append(field)
        
    def get_field_index(self, field: Field) -> int:
        field_id = id(field)
        for idx in range(len(self.fields)):
            if id(self.fields[idx]) == field_id:
                return idx
        return -1
    
    def add_fields_at_index(self, fields: List[Field], idx: int):
        self.fields = self.fields[:idx] + fields + self.fields[idx:]

    def remove_field(self, field: Field) -> Field:
        field_id = id(field)
        for idx in range(len(self.fields)):
            if id(self.fields[idx]) == field_id:
                return self.fields.pop(idx)
        return None

    def update_type(self, ty):
        # if self.type == None: self.type = ty
        self.type = ty
        return self.type == ty
        
    def __repr__(self):
        o = "Record("
        o += f"name={self.name}, type={self.type}, fields=["
        for f in self.fields:
            o += f"{f}, "
        # remove last comma and space
        if len(self.fields) > 0: o = o[:-2]
        o += "])"
        return o
    
    def __str__(self):
        ret = f"{self.name} ::="
        if self.type != Record.UNION: prefix = " "*(len(ret)+1)
        else: prefix = " "*(len(ret) - 1) + "| "
        ret += " " + str(self.fields[0]) + "\n"
        for f in self.fields[1:]:
            ret += prefix + str(f) + "\n"
        return ret
    
    def __eq__(self, other):
        if type(other) != Record: return False
        if self.name != other.name: return False
        if self.type != other.type: return False
        if len(self.fields) != len(other.fields): return False
        if self.type == Record.UNION:
            field_map = {}
            for f in self.fields:
                field_map[f.name] = f
            for f in other.fields:
                if f.name not in field_map: return False
                if field_map[f.name] != f: return False
        else:
            for idx in range(len(self.fields)):
                if self.fields[idx] != other.fields[idx]: return False
        return True

class TestLang:
    def __init__(self):
        self.records: Dict[str, Record] = OrderedDict()

    def check(self):
        if INPUT not in self.records:
            parse_error("Input format must have only one {INPUT} record")

    def add_record(self, record: Record):
        name = record.name
        self.records[name] = record

    def __str__(self):
        ret = ""
        for name in sorted(self.records.keys()):
            ret += str(self.records[name]) + "\n"
        return ret
    
    def __eq__(self, other):
        if type(other) != TestLang: return False
        if len(self.records) != len(other.records): return False
        for name in self.records.keys():
            if name not in other.records: return False
            if self.records[name] != other.records[name]: return False
        return True

def parse_error(msg: str):
    # print(f"Parse error: {msg}")
    raise SyntaxError(msg)

def split_two(txt: str, key: str) -> Tuple[str, str]:
    ret = txt.split(key)
    if len(ret) != 2:
        parse_error(f"There are more than one {key} in {txt}")
    return (ret[0].strip(), ret[1].strip())

def parse_name(line: str) -> Tuple[str, str]:
    line = line.strip()
    size = len(line)
    ret = ""
    if line[0].isalpha(): ret += line[0]
    else: parse_error(f"name must start with alphabet but start with {line[0]}")

    for idx in range(1, size):
        c = line[idx]
        if c.isalnum() or c in NAME_ALLOWED:
            ret += c
        else: return (ret, line[idx:].strip())
    return (ret, "")

def parse_attr(line: str) -> Dict[str, Union[str, int, List[str]]]:
    if line[0] != "{" or line[-1] != "}":
        parse_error(f"attribute must start and end with `{{` and `}}`, respectively, but has {line}")
    line = line[1:-1]
    ret = {}

    line = ''.join(line.split())
    start_idx = 0
    comma_idx = 0
    while True:
        colon_idx = line.find(':', start_idx)
        attr_key = line[start_idx:colon_idx]
        # parse multi-values and verify later that key is correct
        if line[colon_idx + 1] == '[':
            end_idx = line.find(']', colon_idx + 1)
            value_list = line[colon_idx+2:end_idx].split(',')
            for (idx, val) in enumerate(value_list):
                try:
                    value_list[idx] = int(val, 0)
                except:
                    parse_error(f'multi-value attribute must only contain numeric values, but has {val}')
            attr_value = value_list
            if end_idx + 1 < len(line) and line[end_idx + 1] != ',':
                parse_error(f'symbol after multi-value should be comma, but is {line[end_idx + 1]}')
            comma_idx = end_idx + 1
            ret[attr_key] = attr_value
        else:
            comma_idx = line.find(',', colon_idx + 1)
            end_idx = comma_idx
            if end_idx > len(line) or end_idx == -1:
                end_idx = len(line)
            attr_value = line[colon_idx+1:end_idx]
            try:
                ret[attr_key] = int(attr_value, 0)
            except:
                ret[attr_key] = attr_value
        start_idx = comma_idx + 1
        if comma_idx == -1 or start_idx >= len(line):
            break
    return ret

def parse_cnt_attr(line: str) -> Dict[str, Union[str, int]]:
    if line[0] != "[" or line[-1] != "]":
        parse_error(f"cnt attribute must start and end with `[` and `]`, respectively, but has {line}")
    # NOTE supporting numeric cnt is an extension of original grammar
    try:
        name = int(line[1:-1], 0)
    except:
        name = parse_name(line[1:-1])[0]
    return {CNT: name}

def parse_field(line: str) -> Field:
    (name, line) = parse_name(line)
    if len(line) == 0:  return Field(name, Field.Record)
    if line[0] == "[":
        attr = parse_cnt_attr(line)
        return Field(name, Field.Array, attr)
    elif line[0] == "{":
        attr = parse_attr(line)
        return Field(name, Field.Normal, attr)
    parse_error(f"Unknown attribute starts with {line[0]}")

def parse_test_lang(txt: str) -> TestLang:
    lang = TestLang()
    cur = None
    for line in txt.split("\n"):
        # strip comment
        line = line.split("//")[0]
        line = line.strip()
        if line == "": continue
        if ASSIGN in line:
            (assignee, line) = split_two(line, ASSIGN)
            cur = Record(assignee)
            lang.add_record(cur)
        
        if line.startswith(OR):
            # if not cur.update_type (Record.UNION):
            #     parse_error(f"{cur.name} is not `or` typed record.")
            cur.update_type (Record.UNION)
            (_, line) = split_two(line, OR)
        else:
            if cur.type and cur.type == Record.UNION:
                parse_error(f"{cur.name} has already been declared as union type, but has sequential field {line}")
            cur.update_type (Record.SEQ)
        field = parse_field(line)
        cur.add_field(field)
    lang.check()
    return lang

def reduce_record(record: Record, testlang: TestLang):
    if len(record.fields) == 1 and record.fields[0].type == Field.Record:
        inner_record = testlang.records[record.fields[0].name]
        record.type = inner_record.type
        record.fields = inner_record.fields
        # print(f'Reducing {inner_record.name}')
        reduce_record(record, testlang)
    else:
        for f in record.fields:
            if f.type == Field.Record:
                inner_record = testlang.records[f.name]
                reduce_record(inner_record, testlang)

def reduce_test_lang(tl: TestLang) -> TestLang:
    for r in tl.records:
        reduce_record(tl.records[r], tl)
    return tl

def rename_func(tl, old_name, rename_idx):
    new_name = ''
    rename_str = 'RENAME'
    # find unused name in records
    while True:
        new_name = f'{rename_str}{rename_idx}'
        cont_flag = False 
        # I want my labelled breaks/continues...
        for record in tl.records.values():
            if record.name == new_name:
                cont_flag = True
                break
            for field in record.fields:
                if field.name == new_name:
                    cont_flag = True
                    break
            if cont_flag:
                break
        if cont_flag:
            rename_idx += 1
            continue
        break
    # print(new_name)
    # update fields that reference this record
    for record in tl.records.values():
        for field in record.fields:
            if field.name == old_name:
                field.name = new_name
            for a in field.attrs:
                if field.attrs[a] == old_name:
                    field.attrs[a] = new_name
    # update testlang's record map and the record itself
    if old_name in tl.records:
        old_record = tl.records.pop(old_name)
        old_record.name = new_name
        tl.records[new_name] = old_record
    return (tl, rename_idx)

def rename_from_command(tl):
    rename_idx = 0
    (tl, rename_idx) = rename_func(tl, 'COMMAND', rename_idx)
    (tl, rename_idx) = rename_func(tl, 'COMMAND_CNT', rename_idx)
    return tl

# we'll end up also modifying original testlang b/c deepcopy not impl
def rename_command(tl: TestLang) -> TestLang:
    tl = rename_from_command(tl)
    # print('After first pass')
    # print(str(tl))
    input_record = tl.records[INPUT]
    input_is_seq = input_record.type != Record.UNION
    if ( input_record.type != Record.UNION and
         len(input_record.fields) == 2 and 
         input_record.fields[0].type == Field.Normal and
         input_record.fields[1].type == Field.Array and
         input_record.fields[1].attrs[CNT] == input_record.fields[0].name ):
        old_name = input_record.fields[1].name
        tl.records[INPUT].fields[0].name = 'COMMAND_CNT'
        tl.records[INPUT].fields[1].name = 'COMMAND'
        tl.records[INPUT].fields[1].attrs[CNT] = 'COMMAND_CNT'
        old_record = tl.records.pop(old_name)
        old_record.name = 'COMMAND'
        tl.records['COMMAND'] = old_record
    return tl

if __name__ == "__main__":
    sample = """
    // INPUT is the start of the input format.
    // INPUT will be [CMD_CNT (4byte) ][ CMD_CNT chunks of CMD]
    INPUT ::= CMD_CNT { size: 4 }
              CMD[CMD_CNT]

    // CMD will be CMD1 or CMD2 if the example program has two commands.
    CMD   ::= CMD1
            | CMD2

    CMD1  ::= OPCODE { size: 4, value: 0 } // OPCODE is 4 byte and its value is 0.
              FLAG { size: 4 }
              DATA1_SIZE { size: 4 }
              DATA1 { size: DATA1_SIZE }     // the size of DATA1 is DATA1_SIZE
              DATA2_SIZE { size: 4 }
              DATA2 { size: DATA2_SIZE }

    CMD2  ::= OPCODE { size: 4, value: 1}
              FLAG { size: 4}
    """
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            grammar = f.read()
        lang = parse_test_lang(grammar)
        print(f'Original\n{str(lang)}')
        lang = rename_command(lang)
        print(str(lang))
    else:
        lang = parse_test_lang(sample)
        txt = str(lang)
        lang2 = parse_test_lang(txt)
        assert(lang == lang2)
        assert(txt == str(lang2))
        print(txt)
