
# Usage: python tools/verify_answer_syntax.py
import os
import sys
from pathlib import Path
import json
import re
from .test_lang import parse_test_lang

THIS_PATH = Path(os.path.abspath(os.path.dirname(__file__)))

def set_dir():
    # Set working dir to .. relative to this file
    os.chdir(THIS_PATH / "..")

# Reset the working directory
def reset_dir():
    os.chdir(THIS_PATH)

# verify answer method that takes file as input
def verify_answer(file: str) -> bool | SyntaxError:
    with open(file, "rt") as f:
        content = f.read()
    try:
        parse_test_lang(content)
        return True
    except SyntaxError as se:
        # print(f"Parse error: {se}")
        # return False
        return se

if __name__ == "__main__":
    set_dir()
    dir_prefix = "answers"
    # for every text file in ./{dir_prefix}
    for file in os.listdir(f'./{dir_prefix}'):
        if file.endswith(".txt"):
            print(f'Verifying answer file ./{dir_prefix}/{file} ', end="")
            verify_result = verify_answer(f'./{dir_prefix}/{file}')
            if not verify_result or isinstance(verify_result, SyntaxError):
                print(f"- FAILED\n-> {verify_result}")
            else:
                print("- PASSED")
    # reset_dir() # Not needed?
