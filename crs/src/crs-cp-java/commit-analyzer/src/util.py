import glob
import os
import json
from typing import List, Dict
from difflib import unified_diff


def make_sorted_test_set(path) -> List[Dict[str, str]]:
    # To collect data from sub-bug types (e.g., out-of-bound and out-of-bound-read)
    dirs = glob.glob(f"{path}*")

    dataset = []
    for dir in dirs:
        files = os.listdir(dir)
        for f in files:
            file_path = os.path.join(dir, f)
            with open(file_path, "r") as syz_f:
                data = json.load(syz_f)
                # TODO check cases that generate code from scratch are needed
                if data["benign"] is None or data["vulnerable"] is None:
                    continue
            # TODO change data to Code to use same code for fewshot and question
            dataset.append(data)
    dataset.sort(key=lambda x: len(str(x)), reverse=False)
    return dataset


def diff_code(before_code, after_code):
    diff = unified_diff(before_code.split("\n"), after_code.split("\n"))

    filterd_diff = [
        line for line in diff if not (line.startswith("---") or line.startswith("+++"))
    ]

    return "\n".join(filterd_diff)
