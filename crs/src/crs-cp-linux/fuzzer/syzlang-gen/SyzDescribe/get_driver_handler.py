import openai
import os, sys
import re

from llm_util import prompt_llm

MAX_TRIES = 5

assert len(sys.argv) == 3, f"Usage: python {__file__} <relative path to driver code> <realpath to kernel source>" + str(sys.argv)

source_base = os.path.realpath(sys.argv[2])
relpath = sys.argv[1]
# knowledge_file = sys.argv[2]


# parse knowledge file for possible handler struct names
# matches = re.findall(r'".?struct\.(.+)"', open(knowledge_file).read().strip())

# matches = set(matches)

matches = {"drm_driver", "block_device_operations", "device", "file_operations"}

# print(matches)

matches_list = "\n".join([" - " + i for i in matches])

# print(matches_list)

system_prompt = f"""Your task is to look at source code and tell me the name of the struct type of the device handler is.

The device handler is typically inside another struct. It contains pointers to functions to call when the device is being interacted with.

I will now provide an example of what the type is. In the line
`static struct x y = {{}}`, `x` is the type while `y` is the name of the variable.

Your options are:

{matches_list}

Now, look at the following code.
"""

source = open(os.path.join(source_base, relpath)).read().strip()

query = f"""
What is the type and name of the handler? No yapping. Do not expand any string-format characters. Do not include any extra information in your response. Your output should be formatted as the following:
[type] [name]
where you would replace [type] with the type and [name] with the name.
"""

user_prompt = f"""
{source}

{query}
"""

answer = prompt_llm([
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
])

def invalid(s):
    if s.split(" ") == 2:
        a = s.split(" ")
        if a[0] in matches_list:
            return turned

    return False

while MAX_TRIES > 0 and invalid(answer):
    answer = prompt_llm([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "user", "content": f"Your last choice, {answer}, was either invalid or incorrect and thus was not accepted. Think through your steps, and try again."},
        {"role": "user", "content": query}
    ])
    MAX_TRIES -= 1

if invalid(answer):
    # gave up
    print("struct.file_operations")
else:
    print("struct." + answer)