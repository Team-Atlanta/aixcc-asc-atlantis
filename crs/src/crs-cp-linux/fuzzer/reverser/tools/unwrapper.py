from typing import Any, Dict, Set, Tuple, List
from .test_lang import TestLang, Record, Field, parse_test_lang
from .sample import sample10, sample19, sample21, sample22
from .unroller import unroller
from copy import deepcopy
import sys

'''
Algorithm:

Iterate through records
Keep track of the dependencies associated with each record name
Keep track of leafs (records with 0 dependecies remaining)
Keep track of non-leafs (let's call them "remaining_records")
Dependencies can only come from Record fields



*Keep iterating through the remaining records until either no more leaf records exist or no more remaining_records exist | For now, also end if you go a full loop without modification



Assign every duplicate occurance a number?



When you come across a remaining_record that only has leaf nodes as dependencies, then replace each occurances of the leaf in the parent with the content of the leaf its' commands, as follows:

        {RECORDNAME}_{##}_{OLD_COMMAND_NAME}

Where ## means that this is your ##th time copying this child
into the parent

Keep track of the Normal records that have moved in this manner in a dictionary pointing the old value to the new one.
If a future field (Normal or Array) references a value in the dict in their attributes, then replace that value with the updated value



Once you are done with the above, replace the content of the DSL with the new DSL
move the internal node you have just edited to the leaf set



*end_iterations

In theory, the only relevant records in the completed unwrapped DSL are the INPUT record, all of the UNION records, and any RECORD that the UNION record is dependant on, so just return a final testlang containing only those entries
'''
class unwrapper:
    def compute_references(self, tl: TestLang) -> Dict[str, Set[str]]:
        references: Dict[str, Set[str]] = {}
        for rec_name, rec in tl.records.items():
            references[rec_name] = set()
            for field in rec.fields:
                if field.type == Field.Record:
                    references[rec_name].add(field.name)
                if field.type == Field.Array:
                    if type(field.attrs['cnt']) == str:
                        references[rec_name].add(field.name)
                    else:
                        # If it's an int, it should have been caught by the unroller. We should never get here
                        raise ValueError(f"Array field {field.name} in record {rec_name} has a non-string 'cnt' attribute. Instead it is {type(field.attrs['cnt'])}")
        return references

    def prep_replacer(self, tl) -> Tuple[Dict[str, Set[str]], Dict[str, int], Set[str], Set[str]]:
        references: Dict[str, Set[str]] = {}
        usage_counter: Dict[str, int] = {}

        references = self.compute_references(tl)

        internal_nodes: Set[str] = set()
        leafs: Set[str] = set()
        
        # Every record that has no references is a leaf
        # Only SEQ records can be internal nodes
        for rec_name in references:
            usage_counter[rec_name] = 0
            if len(references[rec_name]) == 0 or tl.records[rec_name].type != Record.SEQ:
                leafs.add(rec_name)
            else:
                internal_nodes.add(rec_name)
        
        return references, usage_counter, internal_nodes, leafs


    def __init__(self, tl: TestLang) -> None:
        self.input = tl
        self.unwrapped_test_lang = None

    def expand_arrays_in_test_lang(sefl, tl: TestLang) -> TestLang:
        unrl_tl = unroller.unroll_fixed_size_arrays_in_test_lang(tl)
        return unrl_tl
    
    def replace_record_field_with_record_contents(self, parent_record: Record, record_field: Field, child_record: Record, replacement_number: int) -> None:
        insertion_index = parent_record.get_field_index(record_field)
        x = parent_record.remove_field(record_field)
        # Mapping table to replace references to the old record with the new record
        mapping_table: Dict[str, str] = {}
        fields_to_add = []
        for field in child_record.fields:
            nfield = deepcopy(field)
            # TODO: Replace references to the old record with the new record
            if nfield.type == Field.Normal or nfield.type == Field.Array:
                nfield.name = f"{record_field.name}_{replacement_number}_{nfield.name}"
                for key, value in nfield.attrs.items():
                    if value in mapping_table:
                        nfield.attrs[key] = mapping_table[value]
            # elif nfield.type == Field.Array:
            #     nfield.name = f"{record_field.name}_{replacement_number}_{nfield.name}"
            #     for key, value in nfield.attrs.items():
            #         ...
            mapping_table[field.name] = nfield.name
            fields_to_add.append(nfield)
        parent_record.add_fields_at_index(fields_to_add, insertion_index)
        return



    def replace_all_record_fields_in_test_lang_with_record_contents(self, tl: TestLang) -> TestLang:
        references, usage_counter, internal_nodes, leafs = self.prep_replacer(tl)
        tl = deepcopy(tl)
        # Resolve resolvable records
        update_triggered_last_round = True
        while update_triggered_last_round and len(internal_nodes) > 0 and len(leafs) > 0:
            update_triggered_last_round = False
            internal_nodes_to_remove = set()
            leafs_to_add = set()
            field_replacement_targets = []
            for rec_name in internal_nodes:
                rec = tl.records[rec_name]
                for field in rec.fields:
                    if field.type == Field.Record:
                        if field.name in leafs:
                            # Replace the field with the contents of the leaf
                            if tl.records[field.name].type == Record.UNION:
                                continue
                            field_replacement_targets.append((rec, field, tl.records[field.name], usage_counter[field.name]))
                            usage_counter[field.name] += 1
                            update_triggered_last_round = True
                # If all dependencies are resolved, move to leafs
                if all([dep in leafs for dep in references[rec_name]]):
                    internal_nodes_to_remove.add(rec_name)
                    leafs_to_add.add(rec_name)
                    update_triggered_last_round = True
            for rec_name in internal_nodes_to_remove:
                internal_nodes.remove(rec_name)
            for rec_name in leafs_to_add:
                leafs.add(rec_name)
            for rec, field, child_rec, replacement_number in field_replacement_targets:
                self.replace_record_field_with_record_contents(rec, field, child_rec, replacement_number)
        return tl
    
    def create_minimal_test_lang(self, tl: TestLang) -> TestLang:
        # Starting from the INPUT record, recursively add all records that are dependant on the INPUT record

        # references
        references = self.compute_references(tl)
        record_processing_queue = ['INPUT']
        needed_records: List[str] = []

        while len(record_processing_queue) > 0:
            rec_name = record_processing_queue.pop(0)
            needed_records.append(rec_name)
            for ref in references[rec_name]:
                if ref not in needed_records:
                    record_processing_queue.append(ref)

        # Create a new TestLang with only the needed records
        ntl = TestLang()
        for rec_name in needed_records:
            ntl.add_record(tl.records[rec_name])
        ntl.check()
        return ntl


    # def find_one_to_one_records(self, tl: TestLang) -> List[Tuple[Record, str]]:
    #     one_to_one_records = []
    #     for _rec_name, rec in tl.records.items():
    #         if len(rec.fields) == 1 and rec.fields[0].type == Field.Record:
    #             one_to_one_records.append((rec, rec.fields[0].name))
    #     return one_to_one_records
    
    # def resolve_and_replace_one_to_one_records(self, tl: TestLang, one_to_one_records: List[Tuple[Record, str]]) -> TestLang:
    #     # basically just rename every occurence of the second entry to the first entry's name. This occurs for ANYWHERE it shows up, so both for all of the record names and all of the field names in the testlang
    #     for host_rec, rec_name_to_replace in one_to_one_records:
    #         host_rec_name = host_rec.name
    #         # Replace the matching names of record class objects
    #         for _rec_name, rec in tl.records.items():
    #             if rec.name == rec_name_to_replace:
    #                 rec.name = host_rec_name
    #             for field in rec.fields:
    #                 if field.name == rec_name_to_replace:
    #                     # Accounts for both Record and Array fields
    #                     field.name = host_rec_name
            
    #         # Remove the record once you are done
    #         p = tl.remove_record(rec)
    #         assert p == rec
    #     return tl

    # def find_and_replace_one_to_one_records(self, tl: TestLang) -> TestLang:
    #     # Find all records that have only one field, and that field is a record
    #     ntl = deepcopy(tl)
    #     one_to_one_records = self.find_one_to_one_records(ntl)
    #     if not one_to_one_records:
    #         return ntl
    #     print(f"Found one-to-one records: {one_to_one_records}")
    #     # print(f"Found one-to-one records: {one_to_one_records[0][0]}")
    #     ntl = self.resolve_and_replace_one_to_one_records(tl, one_to_one_records)
    #     return ntl



    def unwrap_test_lang(self, tl: TestLang) -> TestLang:
        ntl = self.expand_arrays_in_test_lang(tl)
        ntl = self.replace_all_record_fields_in_test_lang_with_record_contents(ntl)
        ntl = self.create_minimal_test_lang(ntl)
        # ntl = self.find_and_replace_one_to_one_records(ntl)

        return ntl

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        if not self.unwrapped_test_lang:
            self.unwrapped_test_lang = self.unwrap_test_lang(self.input)
        return self.unwrapped_test_lang
    
def test_unwrapper_s10():
    tl10 = parse_test_lang(sample10)
    print(tl10)
    uw = unwrapper(tl10)()
    print(uw)

def test_unwrapper_s19():
    tl15 = parse_test_lang(sample19)
    print(tl15)
    uw = unwrapper(tl15)()
    print(uw)

def test_unwrapper_s21():
    tl21 = parse_test_lang(sample21)
    print(tl21)
    uw = unwrapper(tl21)()
    print(uw)

def test_unwrapper_s22():
    tl22 = parse_test_lang(sample22)
    print(tl22)
    uw = unwrapper(tl22)()
    print(uw)

if __name__ == '__main__':
    test_unwrapper_s10()
    print("====================================")
    test_unwrapper_s19()
    print("====================================")
    test_unwrapper_s21()
    print("====================================")
    test_unwrapper_s22()
    print("====================================")
    if len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            l = f.read()
        tl = parse_test_lang(l)
        uw = unwrapper(tl)()
        print(uw)
