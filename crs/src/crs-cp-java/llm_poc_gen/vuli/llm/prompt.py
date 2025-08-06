class Prompt:
    _INJECTION_KEYWORD = "/*INJECTION*/"
    _PLACEHOLDER_VULTYPE = "<VULTYPE>"
    _PROMPT_TEMPLATE = f"""
You must suggest the first parameter that is used in fuzzerTestOneInput method.
That byte array is to trigger {_PLACEHOLDER_VULTYPE} vulnerabilities in the given code.
I will give you code under the label <Code> in the below.
{_INJECTION_KEYWORD} is located at right before malicious input injection occurs in the code.
First, I propose STEPs to infer values step by step.

<STEP 1>
The file that is read by fuzzerTestOneInput has at least 1 independent variables.
You MUST answer how many independent variables in the byte array and how they are deserialized from the byte array.

<STEP 2>
You MUST answer how each independent variable is used.

<STEP 3>
Find {_INJECTION_KEYWORD} in the given code and then You MUST answer which independent variables are used to inject malicious input.

<STEP 4>
Find any hints to construct payload in an initializer block. This will help you to know values in field member variables, program environments such as database record etc.

<STEP 5>
You MUST answer exact values for all variables to reach the vulnerable function and inject malicious input to vulnerable function.
When you consider the path to vulnerable function, you MUST infer values based on instructions that can change control flow such as the conditional branches and try catch blocks.

<STEP 6>
Write a python script to make a payload to trigger vulnerability as file whose content will be used the first parameter of fuzzerTestOneInput method.
Please check below requirements:
- First argument of script is a file name.
- Second argument of script is a value for variables identified in <STEP 3>. This will be passed as base64 encoded form.
- Please fill create_payload function in the below code snippet.
import base64
import sys
def create_payload(injection_value):
    ...

if __name__ == "__main__":
    injection_value = base64.b64decode(sys.argv[2])
    with open(sys.argv[1], "wb") as f:
        f.write(create_payload(injection_value))
"""

    def generate(self, sanitizer: str, code: str) -> list[dict]:
        system_prompt = self._create_system_prompt(sanitizer)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"<Code>\n{code}"},
        ]

    def _create_system_prompt(self, sanitizer: str) -> str:
        prompt = Prompt._PROMPT_TEMPLATE
        prompt = prompt.replace(Prompt._PLACEHOLDER_VULTYPE, sanitizer)
        return prompt
