from logging import getLogger
from pathlib import Path

from .lib import TestLang, TTokens
from .template import Command


def get_blob_data(command: Command, path: Path):
    logger = getLogger(__name__)
    data = command.all_fields[path]
    if path not in command.size_constraints:
        return data

    size_constraint_path = command.size_constraints[path]
    size_constraint = int.from_bytes(command.all_fields[size_constraint_path], "little")

    if size_constraint == len(data):
        return data
    elif size_constraint < len(data):
        logger.debug(
            "Data of %s truncated to fit size constraint %s: %d",
            path,
            size_constraint_path,
            size_constraint,
        )
        return data[:size_constraint]
    else:
        logger.debug(
            "Data of %s padded to fit size constraint %s: %d", path, size_constraint_path, size_constraint
        )
        padding = b"\x00" * (size_constraint - len(data))
        return data + padding


def generate_blob_one(command: Command) -> bytes:
    logger = getLogger(__name__)

    buf = bytearray()

    for path in command.serialization_order:
        buf.extend(get_blob_data(command, path))

    logger.debug("Single command blob generated with total size of %d.", len(buf))
    return bytes(buf)


def generate_blob_two(syntax: TestLang, command_list: list[Command]) -> bytes:
    logger = getLogger(__name__)
    input_record = syntax.records[TTokens.INPUT]
    command_len = len(command_list)

    buf = bytearray()

    for field in input_record.fields:
        if "COMMAND_CNT" == field.name:
            # This is safe because "COMMAND_CNT" must have size attribute concrete as it is a first field
            buf.extend(int.to_bytes(command_len, field.attrs[TTokens.SIZE], "little"))  # type: ignore
        elif "COMMAND" == field.name:
            for command in command_list:
                for path in command.serialization_order:
                    buf.extend(get_blob_data(command, path))

    logger.debug("Blob generated with command count of %d with total size of %d.", command_len, len(buf))
    return bytes(buf)
