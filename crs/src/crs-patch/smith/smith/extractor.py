from abc import ABC, abstractmethod
import re
import logging

from typing_extensions import override

from .prompter import Prompt

logger = logging.getLogger(__name__)

PATTERNS = [
    r'```(\w+)?(?P<code>[\s\S]*?)```',  # Triple backticks
]

def findall_by_pattern(message: str):
    output = ""
    for pattern in PATTERNS:
        matches = re.finditer(pattern, message)
        for match in matches:
            output += match.group("code").strip()
    return output

def find_by_pattern(message: str):
    for pattern in PATTERNS:
        match = re.search(pattern, message)
        if match:
            return match.group("code").strip()

    return message

class CodeExtractor(ABC):
    @abstractmethod
    def extract(self, message: str, prompt: Prompt):
        raise NotImplementedError

class FunctionDefExtractor(CodeExtractor):
    @override
    def extract(self, message: str, prompt: Prompt):
        message = find_by_pattern(message)
        lines = message.split('\n')

        # This is required to handle if the function definition is across multiple lines
        # e.g., void foo()\n{
        function_def = prompt.aux["function_def"].split("\n")
        stride = len(function_def)

        for i in range(0, len(lines)):
            if lines[i:i+stride] == function_def:
                lines = lines[i+stride:]
                break

        return '\n'.join(lines)

class ZeroshotExtrapolator(CodeExtractor):
    @override
    def extract(self, message: str, prompt: Prompt):
        message = find_by_pattern(message)

        # The range is from Zeroshot
        to_append = "".join(prompt.footer)

        # cutoff_index = -1
        matched = False
        for i in range(4, 20):
            if len(to_append) > 30-i:
                cutoff = to_append[:30-i].strip()
            else:
                cutoff = to_append.strip()

            if len(cutoff) > 0:
                cutoff_index = message.rfind(cutoff)
                if cutoff_index == -1:
                    continue
                else:
                    matched = True
                    gen_text = message[:cutoff_index]
                    break

        if not matched:
            gen_text = message.rsplit("\n", 1)[0]

        message = gen_text + to_append
        return message

class GoogleExtrapolator(CodeExtractor):
    @override
    def extract(self, message: str, prompt: Prompt):
        message = findall_by_pattern(message)
        message_lines = message.splitlines(keepends=True)

        original_start, original_end = -1, -1
        fixed_start, fixed_end = -1, -1
        for i, line in enumerate(message_lines):
            if "<ORIGINAL>" in line:
                original_start = i+1
            elif "</ORIGINALEND>" in line:
                original_end = i
            elif "<FIX>" in line:
                fixed_start = i+1
            elif "</FIXEND>" in line:
                fixed_end = i

        if any(x == -1 for x in [original_start, original_end, fixed_start, fixed_end]):
            raise ValueError("Incorrect format for GoogleExtrapolator")

        # assert if any of the 4 are -1
        # assert original_start != -1 and original_end != -1, "Original code not properly found"
        # assert fixed_start != -1 and fixed_end != -1, "Fixed code not properly found"

        # Currently only considering single-hunk
        original_body = prompt.aux["original_body"]
        remove_start, remove_end = -1, -1
        for i, line in enumerate(original_body):
            if line.strip() == "":
                continue
            if line.strip() in message_lines[original_start]:
                remove_start, remove_end = i, i + (original_end - original_start)
                break

        if any(x == -1 for x in [remove_start, remove_end]):
            raise ValueError("Original code not found in the prompt")

        # Replace the original code with the fixed code
        return ''.join(
            original_body[:remove_start]
            + message_lines[fixed_start:fixed_end]
            + original_body[remove_end:])
