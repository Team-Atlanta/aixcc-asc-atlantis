import logging

from typing import List
from util import diff_code
from abc import ABC, abstractmethod
from dataset import FunctionChange, CommitChange


class CodeFormatter(ABC):
    def __init__(self, delimiter_type: str) -> None:
        self.delimiter_type = delimiter_type

    @abstractmethod
    def format(self, input: FunctionChange | CommitChange) -> str:
        pass

    def apply_delimiter(self, input: str, format_type: str, key: str = "") -> str:
        if format_type == "none":
            return input
        elif format_type == "xml":
            return f"<{key}>{input}</{key}>"
        elif format_type == "triplequote":
            return f'"""{input}"""'
        else:
            logging.warning(f"Unknown delimiter type: {format_type}")
            return input


class DiffFormatter(CodeFormatter):
    def format(self, input: FunctionChange):
        diff = diff_code(input.before_code, input.after_code)
        diff = self.apply_delimiter(diff, self.delimiter_type, "diff")
        return f"{diff}"


class AfterFunctionFormatter(CodeFormatter):
    def format(self, input: FunctionChange):
        after_code = self.apply_delimiter(input.after_code, self.delimiter_type, "code")
        return f"{after_code}"


class BeforeFunctionFormatter(CodeFormatter):
    def format(self, input: FunctionChange):
        before_code = self.apply_delimiter(
            input.before_code, self.delimiter_type, "code"
        )
        return f"{before_code}"


class FormatterCompose:
    def __init__(self, formatter: List[CodeFormatter]) -> None:
        self.formatters = formatter

    def format(self, input: FunctionChange) -> str:
        formatted_output = []
        for formatter in self.formatters:
            formatted_output.append(formatter.format(input))
        return "\n".join(formatted_output)

    def apply(self, input: FunctionChange | CommitChange) -> str:
        if isinstance(input, FunctionChange):
            return self.format(input)
        elif isinstance(input, CommitChange):
            funcs = []
            for func in input.function_changes:
                funcs.append(self.format(func))
            return "\n\n".join(funcs)
