from abc import ABC, abstractmethod
from typing import List, Optional
import re

from typing_extensions import override

class CodeWriter(ABC):
    # TODO: Update the constructor and remove the _line parameter
    def __init__(self, _line: Optional[str]):
        self._lines: List[str] = []

    def get_indentation(self) -> str:
        if len(self._lines) == 0:
            return ""

        line = self._lines[-1]
        match = re.match(r'^[^\S\n]*', line)
        if match:
            return match.group(0)
        else:
            return ""

    def append(self, *args: str, indenting: bool = False):
        indent = self.get_indentation() if indenting else ""

        for lines in args:
            self._lines.append(indent + lines)

    def append_comment(self, *args: str, indenting: bool = False, block: bool = False):
        indent = self.get_indentation() if indenting else ""

        # Remove the trailing newline
        if block:
            symbol = self.get_block_comment_start_symbol()
        else:
            symbol = self.get_line_comment_symbol()

        for lines in args:
            if lines.endswith("\n"):
                lines = lines[:-1]

            for line in lines.split("\n"):
                self._lines.append(indent + symbol + line + "\n")
                if block:
                    symbol = self.get_block_comment_middle_symbol()

        if block:
            self._lines.append(indent + self.get_block_comment_end_symbol() + "\n")

    @abstractmethod
    def get_line_comment_symbol(self) -> str:
        pass

    def flush(self) -> List[str]:
        return self._lines

    @abstractmethod
    def get_block_comment_start_symbol(self) -> str:
        pass

    @abstractmethod
    def get_block_comment_middle_symbol(self) -> str:
        pass

    @abstractmethod
    def get_block_comment_end_symbol(self) -> str:
        pass

class CCodeWriter(CodeWriter):
    @override
    def get_line_comment_symbol(self) -> str:
        return "// "

    @override
    def get_block_comment_start_symbol(self) -> str:
        return "/* "

    @override
    def get_block_comment_middle_symbol(self) -> str:
        return " * "

    @override
    def get_block_comment_end_symbol(self) -> str:
        return " */"

class PythonCodeWriter(CodeWriter):
    @override
    def get_line_comment_symbol(self) -> str:
        return "# "

    @override
    def get_block_comment_start_symbol(self) -> str:
        return '"""'

    @override
    def get_block_comment_middle_symbol(self) -> str:
        return ''

    @override
    def get_block_comment_end_symbol(self) -> str:
        return '"""'

class JavaCodeWriter(CodeWriter):
    @override
    def get_line_comment_symbol(self) -> str:
        return "// "

    @override
    def get_block_comment_start_symbol(self) -> str:
        return "/* "

    @override
    def get_block_comment_middle_symbol(self) -> str:
        return " * "

    @override
    def get_block_comment_end_symbol(self) -> str:
        return " */"
