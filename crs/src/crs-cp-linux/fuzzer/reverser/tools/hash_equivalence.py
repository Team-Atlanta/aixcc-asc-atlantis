import sys
import os
from .test_lang import Field, TestLang, Record, parse_test_lang, reduce_test_lang
from .tokens import INPUT, NORMAL_ANNOTATION_ATTRS

# hashseed = os.getenv('PYTHONHASHSEED')
# if not hashseed:
#     os.environ['PYTHONHASHSEED'] = '0'
#     os.execv(sys.executable, [sys.executable] + sys.argv)

# I think attr referencing non-int only happens in sequence. So ordering of fields matters, and we can use index.
def hash_attr(attr, attrs, field, available_fields, strict):
    field_names = [f.name for f in available_fields]
    if attrs[attr] in field_names:
        return hash((attr, f'FIELD{field_names.index(attrs[attr])}'))
    if isinstance(attrs[attr], list):
        return hash((attr, tuple(sorted(attrs[attr]))))
    return hash((attr, attrs[attr]))

def hash_field(field, available_fields, record_lookup, strict):
    hash_builder = []

    if field.type == Field.Normal:
        hash_builder.append(0)
    elif field.type == Field.Record:
        hash_builder.append(1)
    elif field.type == Field.Array:
        hash_builder.append(2)

    if field.type == Field.Normal:
        for attr in sorted(field.attrs.keys()):
            if not strict and attr in NORMAL_ANNOTATION_ATTRS:
                continue
            hash_builder.append(hash_attr(attr, field.attrs, field, available_fields, strict))
    elif field.type == Field.Array:
        for attr in sorted(field.attrs.keys()):
            hash_builder.append(hash_attr(attr, field.attrs, field, available_fields, strict))
        hash_builder.append(hash_record(record_lookup[field.name], record_lookup, strict))
    elif field.type == Field.Record:
        hash_builder.append(hash_record(record_lookup[field.name], record_lookup, strict))

    return hash(tuple(hash_builder))

def hash_record(record, record_lookup, strict):
    all_fields = record.fields.copy()
    hash_builder = []
    if record.type == Record.UNION:
        for field in record.fields:
            hash_builder.append(hash_field(field, [], record_lookup, strict))
        hash_builder.sort()
        hash_builder.insert(0, Record.UNION)
    else:
        hash_builder = [Record.SEQ];
        for field in record.fields:
            hash_builder.append(hash_field(field, all_fields, record_lookup, strict))
    return hash(tuple(hash_builder))
    

def hash_testlang(testlang, strict):
    input_record = testlang.records[INPUT]
    top_level_hash = hash_record(input_record, testlang.records, strict)
    return top_level_hash

def is_equivalent(harness1, harness2, strict=True):
    try:
        testlang1 = parse_test_lang(harness1)
        testlang2 = parse_test_lang(harness2)
        hashed1 = hash_testlang(testlang1, strict)
        hashed2 = hash_testlang(testlang2, strict)
        return hashed1 == hashed2
    except:
        return False
    
if __name__ == '__main__':
    # prints hash, set PYTHONHASHSEED=0 for deterministic hashes
    if len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            harness1 = f.read()
        testlang = parse_test_lang(harness1)
        hashed = hash_testlang(testlang)
        print(hashed)
    elif len(sys.argv) == 3:
        # Test if 2 harnesses are equal
        with open(sys.argv[1]) as f:
            harness1 = f.read()
        with open(sys.argv[2]) as f:
            harness2 = f.read()
        print(is_equivalent(harness1, harness2))
