from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import subprocess
import os
import tempfile
import logging

from typing_extensions import override

from .lib.langparser.javaparser import JavaParser
from .lib.langparser.cparser import CParser

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class FunctionInfo:
    name: Optional[str]
    start: int  # 0-based, inclusive
    end: int    # 0-based, inclusive
    src: Path

@dataclass(frozen=True)
class CodeAnalyzer(ABC):
    _file: Path

    @abstractmethod
    def find_function(self, span: Tuple[int, int]) -> FunctionInfo:
        pass

class CCodeAnalyzer(CodeAnalyzer):
    def __init__(self, file: Path, compile_args: List[str]):
        super().__init__(file)
        self._compile_args = compile_args
        self._declarations: Dict = {}

        self._initialize_decl_getters()

    def _initialize_decl_getters(self):
        # CursorKind.FUNCTION_DECL.name
        self._decl_getter_factory("func", "FUNCTION_DECL", "There is no such function.")
        # CursorKind.STRUCT_DECL.name
        self._decl_getter_factory("struct", "STRUCT_DECL", "There is no such struct.")
        # CursorKind.ENUM_DECL.name
        self._decl_getter_factory("enum", "ENUM_DECL", "There is no such enum.")
        # CursorKind.TYPEDEF_DECL.name
        self._decl_getter_factory("typedef", "TYPEDEF_DECL", "There is no such typedef.")
        # CursorKind.VAR_DECL.name
        self._decl_getter_factory("global_var", "VAR_DECL", "There is no such global_var.")

    def _initialize_decls_lazy(self):
        if self._declarations:
            return

        parser = CParser.parse_file(self._file, self._compile_args)
        self._declarations = parser.declarations

    def _decl_getter_factory(self, getter_decl_name, decl_type_name, error_message):
        # define getter
        def get_decl_names():
            self._initialize_decls_lazy()
            return self._declarations \
                        .get(decl_type_name, {}) \
                        .keys()
        # set as method
        setattr(self, f"get_{getter_decl_name}_names", get_decl_names)

        def get_decl_info(name):
            self._initialize_decls_lazy()
            return self._declarations \
                        .get(decl_type_name, {}) \
                        .get(name, None)
        setattr(self, f"get_{getter_decl_name}_info", get_decl_info)

        def get_decl_code(name):
            info = getattr(self, f"get_{getter_decl_name}_info")(name)
            if info is None:
                return error_message
            else:
                return info.code
        setattr(self, f"get_{getter_decl_name}_code", get_decl_code)

    def _find_function_using_clang(self, span: Tuple[int, int]) -> FunctionInfo:
        start, end = span
        assert self._file.exists()
        parser = CParser.parse_file(self._file, self._compile_args)
        for node in parser.walk():
            if node.kind in ['FUNCTION_DECL', 'CXX_METHOD', 'FUNCTION_TEMPLATE'] \
                and str(node.file) == str(self._file) \
                and node.start <= start \
                and end <= node.end:

                return FunctionInfo(node.value, node.start - 1, node.end - 1, self._file)

        raise ValueError('Fail to find vulnerable function')

    def _find_block_using_stack(self, lines: List[str], end: int) -> Tuple[int, int]:
        stack = []

        for cur, line in enumerate(lines):
            if line.startswith("//"):
                continue

            for c in line:
                if c == '{':
                    stack.append(cur)
                elif c == '}':
                    begin = stack.pop()

                    if len(stack) == 0 and cur >= end:
                        return begin, cur
        raise ValueError('Fail to find block end')

    def _find_empty_line_before_start(self, lines: List[str], start: int) -> int:
        for line_idx in range(start, -1, -1):
            line = lines[line_idx].rstrip()
            if all(c in (" ", "\t") for c in line):
                return line_idx

        raise ValueError('Fail to find empty line')

    def _find_function_using_stack(self, _span: Tuple[int, int]) -> FunctionInfo:
        start, end = _span

        lines = open(self._file, 'r').readlines()
        block_begin, block_end = self._find_block_using_stack(lines, end - 1)
        # Heuristic: Use the first empty line before the block + 1 as the function start
        func_start = self._find_empty_line_before_start(lines, block_begin) + 1
        func_end = block_end
        assert func_start <= start and end <= func_end
        return FunctionInfo(None, func_start, func_end, self._file)

    def _generate_ctags(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=True) as f:
            subprocess.run(f'ctags --c-kinds=f -n --format=1 -o {f.name} {os.fspath(self._file)}',
                           shell=True, check=True)
            return [line.split('\t') for line in f.readlines() if not line.startswith('!')]

    def _find_function_using_ctags(self, span: Tuple[int, int]) -> FunctionInfo:
        start, end = span
        tags = self._generate_ctags()

        # XXX: This logic is incorrect!
        # it assumes that the next function is located at the end of the current function.
        # This is not always true, especially when there are multiple spaces between functions.
        func_start = max(
            filter(lambda x: int(x[2]) <= start, tags),
            key=lambda x: int(x[2]))

        func_end = min(
            filter(lambda x: int(x[2]) >= end, tags),
            key=lambda x: int(x[2]))

        return FunctionInfo(
            None,
            int(func_start[2]) - 1,
            int(func_end[2]) - 2,
            self._file
        )

    @override
    def find_function(self, span: Tuple[int, int]) -> FunctionInfo:
        function_lists = [
            self._find_function_using_clang,
            self._find_function_using_ctags,
            self._find_function_using_stack,
        ]

        for func in function_lists:
            try:
                logger.debug(f"Trying to find the function using {func.__name__}")
                ret = func(span)
                logger.debug(f"Found the function using {func.__name__}")
                return ret
            except Exception: # pylint: disable=broad-exception-caught
                logger.debug(f"Failed to find the function using {func.__name__}")

        raise ValueError('Fail to find vulnerable function with all methods')


class PythonCodeAnalyzer(CodeAnalyzer):
    @override
    def find_function(self, _span: Tuple[int, int]) -> FunctionInfo:
        raise NotImplementedError


class JavaCodeAnalyzer(CodeAnalyzer):
    @override
    def find_function(self, span: Tuple[int, int]) -> FunctionInfo:
        start, end = span
        assert self._file.exists()
        parser = JavaParser.parse_file(self._file)
        for node in parser.walk():
            if node.kind == 'MethodDeclaration' or node.kind == 'ConstructorDeclaration':
                if node.start - 1 <= start and end <= node.end + 1:
                    # TODO: Resolve function name in JAVA code analysis
                    return FunctionInfo(None, node.start - 1, node.end - 1, self._file)

        raise ValueError('Fail to find vulnerable function')
