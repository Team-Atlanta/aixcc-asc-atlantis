import openai
import os, sys

from llm_util import prompt_llm

assert len(sys.argv) == 3, f"Usage: python {__file__} <relative path to driver code> <realpath to kernel source>"

source_base = os.path.realpath(sys.argv[2])
relpath = sys.argv[1]

source = open(os.path.join(source_base, relpath)).read().strip()


system_prompt = f"""You are an expert in Linux kernel devices.

Your task is to understand some provided source code, and then answer some questions about it.
"""

user_prompt = f"""Consider the following code for a Linux kernel driver.

```
{source}
```

No yapping. Please tell me the name of the driver that will be exposed to the user. Do not expand any string-format characters. Do not include any extra information or punctuation in your response, just the raw driver name.
"""

answer = prompt_llm([
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
])

print(answer)
