from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional

import os


@dataclass
class Node(ABC):
    kind: str
    value: str
    start: int
    end: int
    file: Optional[os.PathLike]


class Parser(ABC):
    @staticmethod
    @abstractmethod
    def parse_file(file: os.PathLike) -> 'Parser':
        pass

    @staticmethod
    @abstractmethod
    def parse_code(code: str) -> 'Parser':
        # TODO: Add temporary filename as parameter
        pass

    @abstractmethod
    def walk(self) -> Iterator[Node]:
        pass
