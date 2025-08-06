from .test_lang import TestLang, Record, Field, parse_test_lang
from typing import Dict, Set
from .tokens import NORMAL_ANNOTATION_ATTRS

class subset_checker:
    
    def field_is_subset(subset: Field, superset: Field) -> bool:
        if type(subset) != type(superset) and not isinstance(subset, Field):
            return False
        if subset.type != superset.type:
            return False
        if subset.type == Field.Normal:
            # Iterate through the dictionaries of the field attrs together
            for key in subset.attrs.keys():
                if key not in superset.attrs.keys():
                    return False
                if subset.attrs[key] in NORMAL_ANNOTATION_ATTRS:
                    if subset.attrs[key] != superset.attrs[key]:
                        return False
        return True
        

    def record_is_subset(subset: Record, superset: Record) -> bool:
        if type(subset) != type(superset) and not isinstance(subset, Record):
            return False
        if len(subset.fields) > len(superset.fields):
            return False
        for i in range(len(subset.fields)):
            if not subset_checker.field_is_subset(subset.fields[i], superset.fields[i]):
                return False
        return True

    def testlang_is_subset(subset: TestLang, superset: TestLang) -> bool:
        if type(subset) != type(superset) and not isinstance(subset, TestLang):
            return False
        if len(subset.records) > len(superset.records):
            return False
        for record_name in subset.records.keys():
            if record_name not in superset.records.keys():
                return False
            if not subset_checker.record_is_subset(subset.records[record_name], superset.records[record_name]):
                return False
        return True

    def is_subset(subset: TestLang | Record | Field, superset: TestLang | Record | Field) -> bool:
        """
        Check if subset is a subset of superset
        Supported types: TestLang, Record, Field
        Note: Assume that inputs already pass equivalence (conguruence) check
        """
        if type(subset) != type(superset):
            return False
        if isinstance(subset, TestLang):
            return subset_checker.testlang_is_subset(subset, superset)
        if isinstance(subset, Record):
            return subset_checker.record_is_subset(subset, superset)
        if isinstance(subset, Field):
            return subset_checker.field_is_subset(subset, superset)
        # Invalid input
        return False

def test_subset():
    from .sample import sample4, sample5, sample13, sample14
    tl4 = parse_test_lang(sample4)
    tl5 = parse_test_lang(sample5)
    tl13 = parse_test_lang(sample13)
    tl14 = parse_test_lang(sample14)

    print("tl4 is subset of tl4:", subset_checker.is_subset(tl4, tl4))
    print("tl4 is subset of tl5:", subset_checker.is_subset(tl4, tl5))
    print("tl5 is subset of tl4:", subset_checker.is_subset(tl5, tl4))
    print("tl4 is subset of tl13:", subset_checker.is_subset(tl4, tl13))
    print("tl4 is subset of tl14:", subset_checker.is_subset(tl4, tl14))



if __name__ == '__main__':
    test_subset()
