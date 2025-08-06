from dataclasses import dataclass
from pathlib import Path


@dataclass
class PrefixSeed:
    content: str
    relative_path: Path


@dataclass
class ErrorSeed:
    message: str


@dataclass
class InitialSeed: ...


@dataclass
class PlainSeed:
    message: str
