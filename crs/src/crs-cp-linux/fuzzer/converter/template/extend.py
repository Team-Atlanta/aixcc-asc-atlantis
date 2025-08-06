from copy import deepcopy
from logging import getLogger
from pathlib import Path

from pwnlib.util.cyclic import cyclic_gen

from . import Command, RecordLocation


def command_fit_field_size(command: Command, target_size_dict: dict[Path, int]) -> Command:
    logger = getLogger(__name__)
    new_command = deepcopy(command)
    logger.info("Starting field fitting for command %s.", command.command_name)
    for record_id in target_size_dict:
        if record_id not in command.size_constraints:
            logger.debug("Field fitting rejected as %s has literal size constraint.", record_id)
            continue

        size_id = command.size_constraints[record_id]
        if size_id in command.constants:
            logger.debug("Field fitting rejected as %s has constant size constraint.", record_id)
            continue

        size_field = command.all_fields[size_id]
        new_size = target_size_dict[record_id]
        logger.debug("Field fitting of %s done with new size of %d.", record_id, new_size)
        new_command.all_fields[size_id] = int.to_bytes(new_size, len(size_field), "little")

    return new_command


def extend_field(command: Command, cyclic: cyclic_gen, record_id: Path, addition: int) -> bool:
    logger = getLogger(__name__)

    cur_field = command.all_fields[record_id]
    cur_length = len(cur_field)

    if record_id not in command.size_constraints:
        logger.info("Field extension rejected as %s has literal size constraint.", record_id)
        return False

    size_id = command.size_constraints[record_id]
    if size_id in command.constants:
        logger.info("Field extension rejected as %s has constant size constraint.", record_id)
        return False

    size_field = command.all_fields[size_id]
    new_size = int.to_bytes(cur_length + addition, len(size_field), "little")

    add_field = b""
    for off in range(0, addition, 4):
        real_size = min(4, addition - off)
        new_cyclic = cyclic.get(4)

        if not isinstance(new_cyclic, bytes):
            raise Exception("Cyclic generator gave broken output")

        if real_size == 4:
            add_field += new_cyclic
        else:
            add_field += new_cyclic[:real_size]

        command.cyclic_map.append((RecordLocation(record_id, cur_length + off), real_size))

    logger.info(
        "Field extension of %s done with %s appended with new size of %d.",
        record_id,
        add_field,
        cur_length + addition,
    )
    # Do not fix all dependent fields to size, finalize size using memory accesses
    command.all_fields[size_id] = new_size
    command.all_fields[record_id] = cur_field + add_field
    return True
