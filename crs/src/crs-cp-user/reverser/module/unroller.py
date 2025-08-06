from .test_lang import TestLang, Record, Field, parse_test_lang
from .tokens import CNT
from .sample import sample6, sample7

class unroller:
    def unroll_fixed_size_arrays_in_record(record: Record) -> Record:
        nrecord = Record()
        nrecord.name = record.name
        nrecord.type = record.type
        for field in record.fields:
            if field.type == Field.Array:
                if (type(field.attrs[CNT]) == int):
                    for _i in range(field.attrs[CNT]):
                        nfield = Field(field.name, Field.Record)
                        nrecord.add_field(nfield)
                else:
                    nrecord.add_field(field)
            else:
                nrecord.add_field(field)
        return nrecord
    def unroll_fixed_size_arrays_in_test_lang(test_lang: TestLang) -> TestLang:
        ntest_lang = TestLang()
        for _record_name, record in test_lang.records.items():
            nrecord = unroller.unroll_fixed_size_arrays_in_record(record)
            ntest_lang.add_record(nrecord)
        return ntest_lang
    
def test_fixed_loop_unroller():
    tl6 = parse_test_lang(sample6)
    tl7 = parse_test_lang(sample7)
    ur_tl6 = unroller.unroll_fixed_size_arrays_in_test_lang(tl6)
    ur_tl7 = unroller.unroll_fixed_size_arrays_in_test_lang(tl7)
    print(ur_tl6)
    print(ur_tl7)
    print(ur_tl6 == ur_tl7)


if __name__ == '__main__':
    test_fixed_loop_unroller()
