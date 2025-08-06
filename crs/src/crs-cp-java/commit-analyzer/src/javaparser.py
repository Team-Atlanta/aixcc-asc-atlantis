from typing import Iterator, Optional, Tuple, Dict
import os
from cparser import CodeAnalyzer, FunctionInfo, CodeInfo

from typing_extensions import override
from dataclasses import dataclass
from javalang.tokenizer import tokenize
from javalang.parser import Parser
from javalang.tree import CompilationUnit, ClassDeclaration
from javalang import tree

import logging


@dataclass
class JavaNode:
    kind: str
    value: str
    start: int
    end: int
    file: Optional[os.PathLike]


def parse(s):
    tokens = tokenize(s)
    parser = Parser(tokens)
    tree = parser.parse()
    return tree


class JavaParser(Parser):
    def __init__(
        self,
        unit: CompilationUnit,
        file: Optional[os.PathLike] = None,
    ):
        self.unit = unit
        self.file = file

    @staticmethod
    def parse_file(file: os.PathLike) -> "JavaParser":
        with open(file, "r") as f:
            code = f.read()

        return JavaParser(parse(code), file)

    @staticmethod
    def parse_code(code: str) -> "JavaParser":
        return JavaParser(parse(code))


def search_in_imports(imports, variable):
    dot_index = variable.find(".")
    lt_index = variable.find("<")

    if dot_index == -1 and lt_index == -1:
        key = variable
    elif dot_index == -1:
        key = variable.split("<")[0]
    elif lt_index == -1:
        key = variable.split(".")[0]
    else:
        key = variable.split(".")[0] if dot_index < lt_index else variable.split("<")[0]
    if key in imports:
        return f"{imports[key]}{key.join(variable.split(key)[1:])}"
    else:
        return variable


def get_type_args(type):
    if type is None:
        return ""
    elif not hasattr(type, "arguments") or type.arguments is None:
        return type.name
    else:
        # Don't know what arg is. Just use arg.type for now
        args = (
            [get_type_name(arg.type) for arg in type.arguments]
            if type.arguments
            else []
        )
        return f"{type.name}<{','.join(args)}>"


def get_type_name(type):
    if not hasattr(type, "sub_type") or type.sub_type == None:
        return get_type_args(type)
    else:
        return f"{get_type_args(type)}.{get_type_name(type.sub_type)}"


def get_class_signatures(node, prefix="", visited=set(), is_inner=False):
    signatures = []
    if isinstance(node, ClassDeclaration):
        if is_inner:
            class_name = f"{prefix}${node.name}" if prefix else node.name
        else:
            class_name = f"{prefix}.{node.name}" if prefix else node.name
        signatures.append(class_name)
        prefix = class_name
        is_inner = True

    visited.add(node)

    for _, child in node.filter(ClassDeclaration):
        if child not in visited:
            signatures.extend(get_class_signatures(child, prefix, visited, is_inner))

    return signatures


class JavaCodeAnalyzer(CodeAnalyzer):
    @override
    def find_function(self, span: Tuple[int, int]) -> FunctionInfo:
        start, end = span
        assert self._file.exists()
        parser = JavaParser.parse_file(self._file)
        for node in parser.walk():
            if (
                node.kind == "MethodDeclaration"
                or node.kind == "ConstructorDeclaration"
            ):
                if node.start - 1 <= start and end <= node.end + 1:
                    # TODO: Resolve function name in JAVA code analysis
                    return FunctionInfo(None, node.start - 1, node.end - 1, self._file)

        raise ValueError("Fail to find vulnerable function")

    def get_all_functions(self) -> Dict[str, CodeInfo]:
        logger = logging.getLogger("JavaCodeAnalyzer")

        declarations = {}
        try:
            parser = JavaParser.parse_file(self._file)
            with open(self._file, "r") as f:
                lines = f.readlines()
        except Exception as e:
            logger.warn(f"Error in parsing file: {e}")
            lines = []
            raise e

        package_name = (
            parser.unit.package.name if parser.unit.package is not None else ""
        )
        imports = {}

        for i in parser.unit.imports:
            if not i.wildcard:
                imports[i.path.split(".")[-1]] = i.path

        classes = get_class_signatures(parser.unit, prefix=package_name)
        for class_def in classes:
            if "$" in class_def:
                imports[class_def.split("$")[-1]] = class_def
            else:
                imports[class_def.split(".")[-1]] = class_def

        for _, node in parser.unit:
            if isinstance(node, ClassDeclaration):
                for m in node.methods:
                    try:
                        if m.return_type is None:
                            return_type = "void"
                        else:
                            return_type = search_in_imports(
                                imports, get_type_name(m.return_type)
                            )

                        method_name = (
                            f"{search_in_imports(imports, node.name)}.{m.name}"
                        )
                        params = [
                            search_in_imports(imports, get_type_name(p.type))
                            for p in m.parameters
                        ]
                        sig = f"{method_name}:{return_type}({','.join(params)})"

                        code = "".join(lines[m.start.line - 1 : m.end.line])
                    except Exception as e:
                        logger.error(f"Error in parsing method: {e}")
                        continue

                    declarations[sig] = CodeInfo(m.start, m.end, self._file, code)

                for constructor in node.constructors:
                    try:
                        method_name = f"{search_in_imports(imports, node.name)}"

                        params = [
                            search_in_imports(imports, get_type_name(p.type))
                            for p in constructor.parameters
                        ]
                        sig = f"{method_name}:{method_name}({','.join(params)})"

                        code = "".join(
                            lines[constructor.start.line - 1 : constructor.end.line]
                        )
                    except Exception as e:
                        logger.error(f"Error in parsing constructor: {e}")
                        continue

                    declarations[sig] = CodeInfo(
                        constructor.start, constructor.end, self._file, code
                    )

        return declarations
