from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ArgumentType(Enum):
    UNKNOWN = 0
    CONST = 1
    EXTERN = 2
    VAR = 3
    MEM = 4


@dataclass(frozen=True)
class RecordLocation:
    location_id: Path
    offset: int


@dataclass(frozen=True)
class Field:
    offset: int
    size: int | None
    insert: bool


@dataclass
class Argument:
    arg_type: ArgumentType
    field_map: dict[Field, RecordLocation]


@dataclass
class Syscall:
    number: int
    arguments: list[Argument]


@dataclass
class Command:
    command_name: str
    syscalls: list[Syscall]
    all_fields: dict[Path, bytes]
    size_fields: set[Path]
    size_constraints: dict[Path, Path]
    constants: set[Path]
    serialization_order: list[Path]
    cyclic_map: list[tuple[RecordLocation, int]]


@dataclass
class Blob:
    commands: list[Command]
