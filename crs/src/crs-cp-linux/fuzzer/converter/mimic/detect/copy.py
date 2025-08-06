import bisect
import dataclasses
from copy import deepcopy
from logging import getLogger
from pathlib import Path

from pwnlib.util.cyclic import cyclic_gen

from ...lib import SSyscall
from ...template import ArgumentType, Command, Field, RecordLocation


def get_size_diff(value: bytes) -> bytes:
    value_len = len(value)
    value_int = int.from_bytes(value, "little")
    return int.to_bytes(value_int + 4, value_len, "little")


def get_insert_diff(value: bytes) -> bytes:
    return b"zzzz" + value


def generate_full_copy_diff_command(command: Command, target_record_field: Path):
    logger = getLogger(__name__)

    logger.debug("Generating full copy detection diff for command %s:", command.command_name)
    command_copy = deepcopy(command)
    original_field = command_copy.all_fields[target_record_field]
    command_copy.all_fields[target_record_field] = get_insert_diff(original_field)
    logger.debug("    - %s", target_record_field)
    logger.debug("         %s", original_field.hex(" ", -4))
    logger.debug("      => %s", command_copy.all_fields[target_record_field].hex(" ", -4))

    if target_record_field in command_copy.size_constraints:
        size_field = command_copy.size_constraints[target_record_field]
        original_field = command_copy.all_fields[size_field]
        command_copy.all_fields[size_field] = get_size_diff(original_field)
        logger.debug("    - %s", size_field)
        logger.debug("         %s", original_field.hex(" ", -4))
        logger.debug("      => %s", command_copy.all_fields[size_field].hex(" ", -4))

    return command_copy


def detect_full_copy_field(
    command: Command, target_record_field: Path, syscalls_zip: list[tuple[SSyscall | None, SSyscall | None]]
) -> bool:
    logger = getLogger(__name__)
    found = False

    if target_record_field in command.size_fields:
        logger.debug(
            "Skipping full copy detection of %s for command %s as it seems like a size related value...",
            target_record_field,
            command.command_name,
        )
        return False

    logger.info(
        "Performing full copy field detection of %s for command %s...",
        target_record_field,
        command.command_name,
    )

    target_seq = command.all_fields[target_record_field]
    logger.debug("Target sequence: %s", target_seq.hex(" ", -4))

    offset = 0

    for syscall_i, (syscall_a, syscall_b) in enumerate(syscalls_zip):
        if syscall_a is None:
            offset -= 1
            continue

        if syscall_b is None:
            continue

        syscall_entry = command.syscalls[syscall_i + offset]
        if syscall_entry.number != syscall_a.sysnum:
            logger.error(
                "Trace syscall numbers doesn't match. This shouldn't happen. Skipping field detection..."
            )
            continue

        visited = set()
        for mem_i, mem in enumerate(syscall_a.in_mems):
            if mem.addr in visited:
                logger.debug("Skipping duplicate address entry 0x%x...", mem.addr)
                continue
            visited.add(mem.addr)

            sorted_args = sorted(syscall_a.args)
            nearest_addr = bisect.bisect_right(sorted_args, mem.addr)

            if nearest_addr == 0:
                continue

            target_region_start = sorted_args[nearest_addr - 1]
            idx = syscall_a.args.index(target_region_start)
            t_offset = mem.addr - target_region_start

            # Memory TOO big?
            if t_offset > 0x1000000:
                continue

            logger.debug(
                "Address argument 0x%x at idx %d chosen for memory address 0x%x.",
                target_region_start,
                idx,
                mem.addr,
            )

            field_off = mem.data.find(target_seq)
            if field_off == -1:
                continue

            logger.debug("Full copy found in address 0x%x.", mem.addr + field_off)
            logger.debug("Memory dump: %s", mem.data.hex(" ", -4))

            if get_insert_diff(target_seq) not in syscall_b.in_mems[mem_i].data:
                logger.debug("Full copy not detected while double checking.")
                logger.debug("Memory dump: %s", syscall_b.in_mems[mem_i].data.hex(" ", -4))
                continue

            insert_check = syscall_b.in_mems[mem_i].size != mem.size
            syscall_entry.arguments[idx].arg_type = ArgumentType.MEM
            field = Field(t_offset + field_off, None, insert_check)
            record_location = RecordLocation(target_record_field, 0)

            if field not in syscall_entry.arguments[idx].field_map:
                found = True
                syscall_entry.arguments[idx].field_map[field] = record_location
                logger.debug(
                    "Syscall entry %d: syscall_%d[%d: mem][%d:] marked %s full copy of record id %s.",
                    syscall_i + offset,
                    syscall_a.sysnum,
                    idx,
                    t_offset + field_off,
                    "insertion mode" if insert_check else "overwriting mode",
                    target_record_field,
                )
            else:
                logger.debug(
                    "Syscall entry %d: syscall_%d[%d: mem][%d:] already marked. Skipping...",
                    syscall_i + offset,
                    syscall_a.sysnum,
                    idx,
                    t_offset + field_off,
                )

        if target_record_field not in command.size_constraints:
            continue

        size_field = command.size_constraints[target_record_field]
        logger.debug("Trying detection of size constraint field %s...", size_field)

        size_value = command.all_fields[size_field]
        size_field_len = len(size_value)
        size_value = int.from_bytes(size_value, "little")
        logger.debug("Target: 0x%x", size_value)

        for idx, arg in enumerate(syscall_a.args):
            if arg != size_value:
                continue

            if syscall_b.args[idx] != size_value + 4:
                logger.debug("Size field not detected while double checking.")
                logger.debug("Found: 0x%x, Expected: 0x%x", syscall_b.args[idx], size_value + 4)
                continue

            syscall_entry.arguments[idx].arg_type = ArgumentType.VAR
            field = Field(0, size_field_len, False)
            record_location = RecordLocation(size_field, 0)
            if field not in syscall_entry.arguments[idx].field_map:
                syscall_entry.arguments[idx].field_map[field] = record_location
                logger.debug(
                    "Syscall entry %d: syscall_%d[%d] mapped to record id %s as size variable.",
                    syscall_i + offset,
                    syscall_a.sysnum,
                    idx,
                    record_location.location_id,
                )
            else:
                logger.debug(
                    "Syscall entry %d: syscall_%d[%d] already marked. Skipping...",
                    syscall_i + offset,
                    syscall_a.sysnum,
                    idx,
                )

    if found:
        logger.info(
            "Record id %s of command %s is marked as full copy field.",
            target_record_field,
            command.command_name,
        )

    return found


def detect_partial_copy_field(
    command: Command, cyclic: cyclic_gen, syscalls: list[SSyscall], blacklist: set[Path]
) -> set[RecordLocation]:
    logger = getLogger(__name__)

    logger.info(
        "Performing partial copy field detection for command %s...",
        command.command_name,
    )

    if len(blacklist) != 0:
        logger.debug("Skipping following record ids as it is marked as full copy:")
        for record_id in blacklist:
            logger.debug("    - %s", record_id)

    mark_count = 0
    marked_location = set()
    for syscall_i, syscall in enumerate(syscalls):
        syscall_entry = command.syscalls[syscall_i]
        if syscall_entry.number != syscall.sysnum:
            logger.error(
                "Trace syscall numbers doesn't match. This shouldn't happen. Skipping field detection..."
            )
            continue

        visited = set()
        for mem in syscall.in_mems:
            if mem.addr in visited:
                logger.debug("Skipping duplicate address entry 0x%x...", mem.addr)
                continue
            visited.add(mem.addr)

            sorted_args = sorted(syscall.args)
            nearest_addr = bisect.bisect_right(sorted_args, mem.addr)

            if nearest_addr == 0:
                continue

            target_region_start = sorted_args[nearest_addr - 1]
            idx = syscall.args.index(target_region_start)
            t_offset = mem.addr - target_region_start

            # Memory TOO big?
            if t_offset > 0x1000000:
                continue

            logger.debug(
                "Address argument 0x%x at idx %d chosen for memory address 0x%x.",
                target_region_start,
                idx,
                mem.addr,
            )

            mem_len = len(mem.data)
            for mem_i in range(0, mem_len, 4):
                end = min(mem_i + 4, mem_len)

                # Too short matches tends to be FP
                if end - mem_i < 3:
                    continue

                if mem.data[end - 1] == 0:
                    cyclic_search = cyclic.find(mem.data[mem_i : end - 1])
                else:
                    cyclic_search = cyclic.find(mem.data[mem_i:end])

                if cyclic_search == -1:
                    continue

                _, chunk, offset = cyclic_search

                if offset != -1:
                    logger.debug("Partial copy found in address 0x%x.", mem.addr + mem_i)
                    logger.debug("Memory dump: %s", mem.data[mem_i:end].hex(" ", -4))

                    record_location, _ = command.cyclic_map[chunk]
                    if record_location.location_id in blacklist:
                        logger.debug("Skipping this as it is marked as full copy...")
                        continue

                    syscall_entry.arguments[idx].arg_type = ArgumentType.MEM
                    field = Field(t_offset + mem_i, end - mem_i, False)
                    record_location = dataclasses.replace(
                        record_location, offset=record_location.offset + offset
                    )

                    if field not in syscall_entry.arguments[idx].field_map:
                        if record_location.offset + end - mem_i > len(
                            command.all_fields[record_location.location_id]
                        ):
                            logger.debug("Skipping this as it overflows record field...")
                            continue

                        syscall_entry.arguments[idx].field_map[field] = record_location
                        for i in range(field.size):  # type: ignore
                            marked_location.add(
                                RecordLocation(record_location.location_id, record_location.offset + i)
                            )
                        mark_count += 1
                        logger.debug(
                            "Syscall entry %d: syscall_%d[%d: mem][%d:%d] marked partial copy of record field %s[%d:%d].",
                            syscall_i,
                            syscall.sysnum,
                            idx,
                            t_offset + mem_i,
                            t_offset + end,
                            record_location.location_id,
                            record_location.offset,
                            record_location.offset + end - mem_i,
                        )
                    else:
                        logger.debug(
                            "Syscall entry %d: syscall_%d[%d: mem][%d:%d] already marked. Skipping...",
                            syscall_i,
                            syscall.sysnum,
                            idx,
                            t_offset + mem_i,
                            t_offset + end,
                        )

        for idx, arg in enumerate(syscall.args):
            byte_arg = int.to_bytes(arg, 8, "little")
            if byte_arg[3] == 0:
                cyclic_search_low = cyclic.find(byte_arg[:3])
            else:
                cyclic_search_low = cyclic.find(byte_arg[:4])

            if cyclic_search_low != -1:
                _, chunk, offset = cyclic_search_low

                if offset != -1:
                    syscall_entry.arguments[idx].arg_type = ArgumentType.VAR
                    record_location, _ = command.cyclic_map[chunk]
                    field = Field(0, 4, False)
                    record_location = dataclasses.replace(
                        record_location, offset=record_location.offset + offset
                    )

                    if field not in syscall_entry.arguments[idx].field_map:
                        if record_location.offset + 4 <= len(
                            command.all_fields[record_location.location_id]
                        ):
                            syscall_entry.arguments[idx].field_map[field] = record_location
                            for i in range(field.size):  # type: ignore
                                marked_location.add(
                                    RecordLocation(record_location.location_id, record_location.offset + i)
                                )
                            mark_count += 1
                            logger.debug(
                                "Syscall entry %d: syscall_%d[%d][%d:%d] mapped to record id %s[%d:%d] as variable.",
                                syscall_i,
                                syscall.sysnum,
                                idx,
                                0,
                                4,
                                record_location.location_id,
                                record_location.offset,
                                record_location.offset + 4,
                            )
                    else:
                        logger.debug(
                            "Syscall entry %d: syscall_%d[%d][%d:%d] already marked. Skipping...",
                            syscall_i,
                            syscall.sysnum,
                            idx,
                            0,
                            4,
                        )

            if byte_arg[7] == 0:
                cyclic_search_high = cyclic.find(byte_arg[4:7])
            else:
                cyclic_search_high = cyclic.find(byte_arg[4:])

            if cyclic_search_high != -1:
                _, chunk, offset = cyclic_search_high

                if offset != -1:
                    syscall_entry.arguments[idx].arg_type = ArgumentType.VAR
                    record_location, _ = command.cyclic_map[chunk]
                    field = Field(4, 4, False)
                    record_location = dataclasses.replace(
                        record_location, offset=record_location.offset + offset
                    )

                    if field not in syscall_entry.arguments[idx].field_map:
                        if record_location.offset + 4 <= len(
                            command.all_fields[record_location.location_id]
                        ):
                            syscall_entry.arguments[idx].field_map[field] = record_location
                            for i in range(field.size):  # type: ignore
                                marked_location.add(
                                    RecordLocation(record_location.location_id, record_location.offset + i)
                                )
                            mark_count += 1
                            logger.debug(
                                "Syscall entry %d: syscall_%d[%d][%d:%d] mapped to record id %s[%d:%d] as variable.",
                                syscall_i,
                                syscall.sysnum,
                                idx,
                                4,
                                8,
                                record_location.location_id,
                                record_location.offset,
                                record_location.offset + 4,
                            )
                    else:
                        logger.debug(
                            "Syscall entry %d: syscall_%d[%d][%d:%d] already marked. Skipping...",
                            syscall_i,
                            syscall.sysnum,
                            idx,
                            4,
                            8,
                        )

            if cyclic_search_low != -1 or cyclic_search_high != -1:
                continue

    logger.info("Total %d items marked as partial copy.", mark_count)
    return marked_location


@dataclasses.dataclass(frozen=True)
class FieldPointer:
    syscall_idx: int
    arg_idx: int
    field: Field


def detect_byte_copy_field(
    command: Command,
    trial_map: dict[RecordLocation, int],
    syscalls: list[SSyscall | None],
    mapping_candidates: dict[RecordLocation, set[FieldPointer]],
):
    logger = getLogger(__name__)
    logger.info(
        "Performing byte copy field detection for command %s...",
        command.command_name,
    )

    byte_map: list[set[FieldPointer]] = [set() for _ in range(256)]

    for syscall_i, syscall in enumerate(syscalls):
        if syscall is None:
            continue

        syscall_entry = command.syscalls[syscall_i]
        if syscall_entry.number != syscall.sysnum:
            logger.error(
                "Trace syscall numbers doesn't match. This shouldn't happen. Skipping field detection..."
            )
            continue

        visited = set()
        for mem in syscall.in_mems:
            if mem.addr in visited:
                logger.debug("Skipping duplicate address entry 0x%x...", mem.addr)
                continue
            visited.add(mem.addr)

            sorted_args = sorted(syscall.args)
            nearest_addr = bisect.bisect_right(sorted_args, mem.addr)

            if nearest_addr == 0:
                continue

            target_region_start = sorted_args[nearest_addr - 1]
            idx = syscall.args.index(target_region_start)
            t_offset = mem.addr - target_region_start

            # Memory TOO big?
            if t_offset > 0x1000000:
                continue

            logger.debug(
                "Address argument 0x%x at idx %d chosen for memory address 0x%x.",
                target_region_start,
                idx,
                mem.addr,
            )
            syscall_entry.arguments[idx].arg_type = ArgumentType.MEM

            for mem_i, mem_byte in enumerate(mem.data):
                field = Field(t_offset + mem_i, 1, False)
                byte_map[mem_byte].add(FieldPointer(syscall_i, idx, field))

        for idx, arg in enumerate(syscall.args):
            if (
                syscall_entry.arguments[idx].arg_type == ArgumentType.CONST
                or syscall_entry.arguments[idx].arg_type == ArgumentType.EXTERN
                or syscall_entry.arguments[idx].arg_type == ArgumentType.MEM
            ):
                continue

            byte_arg = int.to_bytes(arg, 8, "little")
            for byte_arg_i, byte_arg_data in enumerate(byte_arg):
                field = Field(byte_arg_i, 1, False)
                byte_map[byte_arg_data].add(FieldPointer(syscall_i, idx, field))

    for record_location, trial_bytes in trial_map.items():
        if record_location in mapping_candidates:
            mapping_candidates[record_location].intersection_update(byte_map[trial_bytes])
        else:
            mapping_candidates[record_location] = byte_map[trial_bytes]
