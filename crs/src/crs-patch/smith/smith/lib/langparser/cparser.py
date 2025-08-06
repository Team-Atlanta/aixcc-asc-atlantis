from typing import Iterator, List, Dict, Optional
from collections import namedtuple
from pathlib import Path
import os

import clang.cindex # type: ignore

from .parser import Node, Parser

CodeInfo = namedtuple("CodeInfo", "beg, end, file, code")

# TODO: Move this to utils
def load_file(pn: Path) -> List[str]:
    if pn is None:
        return []
    with open(pn, 'r', encoding='utf-8', errors='ignore') as fd:
        return fd.readlines()

class CNode(Node):
    pass

class CParser(Parser):
    def __init__(self, unit: clang.cindex.TranslationUnit):
        self.unit = unit
        self._declarations = self.get_declarations()

    @staticmethod
    def parse_file(file: os.PathLike, args: Optional[List[str]] = None) -> 'CParser':
        if args is None:
            args = []
        return CParser(clang.cindex.Index.create().parse(os.fspath(file), args=args))

    @staticmethod
    def parse_code(code: str) -> 'CParser':
        raise NotImplementedError

    @property
    def declarations(self) -> Dict:
        return self._declarations

    def walk(self) -> Iterator[CNode]:
        for cursor in self.unit.cursor.walk_preorder():
            if cursor.location.file is None:
                fp = None
            else:
                fp = cursor.location.file

            yield CNode(
                kind=cursor.kind.name,
                value=cursor.spelling,
                start=cursor.extent.start.line,
                end=cursor.extent.end.line,
                file=fp
            )

    def get_declarations(self) -> Dict[str, Dict[str, CodeInfo]]:
        declarations: Dict[str, Dict[str, CodeInfo]] = {}
        for cursor in self.unit.cursor.get_children():

            if cursor.kind.value <= 39:
                start_line = cursor.extent.start.line - 1
                end_line = cursor.extent.end.line - 1

                # may not match the file that is being read
                if cursor.extent.start.file is None:
                    continue

                file_name = Path(str(cursor.extent.start.file)).resolve()
                name = cursor.spelling
                lines = load_file(file_name)
                code = "".join(lines[start_line:(end_line + 1)])

                if cursor.kind.name not in declarations:
                    declarations[cursor.kind.name] = {}

                insert = False
                if not name in declarations[cursor.kind.name]:
                    insert = True
                else:
                    info = declarations[cursor.kind.name][name]

                    # Note. it will overwrite the past code
                    # print(f"Duplicate declaration of {name} at {cursor.extent}")

                    # pick a "larger" code ..
                    if len(info.code) < len(code):
                        insert = True

                if insert:
                    declarations[cursor.kind.name][name] \
                        = CodeInfo(start_line, end_line, file_name, code)

        return declarations
