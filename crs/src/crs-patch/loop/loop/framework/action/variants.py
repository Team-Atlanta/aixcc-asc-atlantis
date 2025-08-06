from dataclasses import dataclass


@dataclass
class DiffAction:
    content: str


@dataclass
class WrongFormatAction:
    error: Exception


@dataclass
class RuntimeErrorAction:
    error: Exception
