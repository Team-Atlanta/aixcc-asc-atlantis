from typing import Iterator, Optional
import os

from .parser import Node, Parser
from .. import javalang # pylint: disable=relative-beyond-top-level


class JavaNode(Node):
    pass


class JavaParser(Parser):
    def __init__(self,
                 unit: javalang.parser.tree.CompilationUnit,
                 file: Optional[os.PathLike] = None):
        self.unit = unit
        self.file = file

    @staticmethod
    def parse_file(file: os.PathLike) -> 'JavaParser':
        with open(file, 'r') as f:
            code = f.read()

        return JavaParser(javalang.parse.parse(code), file)

    @staticmethod
    def parse_code(code: str) -> 'JavaParser':
        return JavaParser(javalang.parse.parse(code))

    def walk(self) -> Iterator[JavaNode]:
        for _, node in self.unit:
            if 'name' in node.attrs and getattr(node, 'name') is not None \
                and node.start is not None and node.end is not None:
                if 'annotations' in node.attrs and getattr(node, 'annotations'):
                    start = min(map(lambda n: n.start.line, getattr(node, 'annotations')))
                else:
                    start = node.start.line
                yield JavaNode(
                    kind=type(node).__name__,
                    value=getattr(node, 'name'),
                    start=start,
                    end=node.end.line,
                    file=self.file
                )
