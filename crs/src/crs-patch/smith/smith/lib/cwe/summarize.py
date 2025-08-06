#!/usr/bin/env python3
# pylint: disable=no-member

import sys
import openai # openai == 0.28

CWE = open(sys.argv[1]).read()
OUT = sys.argv[2]

prompt = f"""
We'd like to find security bugs by using large language model
by formulating a prompt that describes security bugs. To do so,
we'd first like to summarize the description of the bug to be put as part of
the prompt. We downloaded the detail description of the type of bugs we are
looking for from the MITRE webpage, which as appended below after the "----"
mark.

Your job is the summarize the bug description in one or two paragraphs as
accurately as possible by extracting the essence of its content, which is useful
for the large language model to find the bug by using it.

----
{CWE}
"""

response = openai.ChatCompletion.create( # type: ignore
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

summary = response.choices[0].message["content"]
print(summary)

with open(OUT, "w") as fd:
    fd.write(summary)
