from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, List
import util


# Dev
@dataclass
class FunctionChange:
    commit_id: str
    function_name: str
    before_code: str
    after_code: str
    before_file: str
    after_file: str
    bug_type: str = "None"


@dataclass
class CommitChange:
    commit_id: str
    function_changes: List[FunctionChange]


FileChange = CommitChange


class DataSet:
    dataset: Dict[str, List[Dict[str, str]]] = dict()

    @abstractmethod
    def collect_dataset():
        pass

    @abstractmethod
    def transform():
        pass


class SyzbotDataSet(DataSet):
    def collect_dataset(self, sanitizers) -> Dict[str, List[Dict[str, str]]]:
        for sanitizer in sanitizers.values():
            (sanitizer_name, bug_type) = sanitizer.split(":")
            sanitizer_name = sanitizer_name.strip()
            bug_type = bug_type.strip()
            dir_name = f"{sanitizer_name}__{bug_type}"

            examples = util.make_sorted_test_set(f"./data/syzbot-function/{dir_name}")
            self.dataset[sanitizer] = examples

    def transform(self):
        transformed_data: List[FunctionChange] = []
        for sanitizer, examples in self.dataset.items():
            bug_type = sanitizer.split(":")[1].strip()
            for example in examples:
                after_code = example["vulnerable"]
                before_code = example["benign"]
                transformed_data.append(
                    FunctionChange(
                        commit_id="None",
                        function_name="None",
                        before_code=before_code,
                        after_code=after_code,
                        before_file="None",
                        after_file="None",
                        bug_type=bug_type,
                    )
                )
        return transformed_data


# UserSpaceDataSet
class OssFuzzDataSet(DataSet):
    def collect_dataset():
        pass

    def transform():
        pass
