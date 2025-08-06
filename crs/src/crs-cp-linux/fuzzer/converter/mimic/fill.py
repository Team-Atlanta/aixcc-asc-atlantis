import dataclasses
from logging import getLogger
from pathlib import Path

from ..lib import SMem, SSyscall
from ..template import ArgumentType, RecordLocation, Syscall
from ..template.extend import extend_field
from . import CommandState


def compilance_diff(trace: SSyscall, target_trace: SSyscall, template_syscall: Syscall):
    if trace.sysnum != target_trace.sysnum:
        return False

    for idx, (arg_base, arg) in enumerate(zip(trace.args, target_trace.args)):
        if template_syscall.arguments[idx].arg_type != ArgumentType.CONST:
            continue

        if arg_base != arg:
            return False

    return True


def get_memory_region_access_info(
    trace: SSyscall,
    last_access_addrs: list[int],
    last_access_records: list[RecordLocation | None],
) -> list[tuple[int, int, int, RecordLocation | None]]:
    logger = getLogger(__name__)

    logger.debug("Starting memory region access summary...")

    def get_memory_region(mem: SMem):
        return (mem.addr, mem.addr + mem.size)

    regions = sorted(
        list(
            zip(
                map(get_memory_region, trace.in_mems),
                last_access_addrs,
                last_access_records,
            )
        ),
        key=lambda x: x[0],
    )

    merged_regions = list()
    current = None

    for (start, end), last_access_addr, last_access_record in regions:
        if current is None:
            current = (start, end, last_access_addr, last_access_record)
            continue
        elif current[1] >= start and current[1] < end:
            logger.debug("Merging (0x%x, 0x%x) with (0x%x, 0x%x)...", start, end, current[0], current[1])
            if current[2] < last_access_addr:
                current = (current[0], end, last_access_addr, last_access_record)
            else:
                current = (current[0], end, current[2], current[3])
        elif current[1] < start:
            merged_regions.append(current)
            current = (start, end, last_access_addr, last_access_record)
        else:
            if current[2] < last_access_addr:
                current = (current[0], current[1], last_access_addr, last_access_record)

    if current is not None:
        merged_regions.append(current)

    logger.debug("Summarization done for memory region accesses:")
    if len(merged_regions) == 0:
        logger.debug("    None")
    else:
        for region in merged_regions:
            start, end, last_access_addr, last_access_record = region
            if last_access_record is None:
                logger.debug("    0x%x @ [0x%x:0x%x] by None", last_access_addr, start, end)
            else:
                logger.debug(
                    "    0x%x @ [0x%x:0x%x] by %s[%d]",
                    last_access_addr,
                    start,
                    end,
                    last_access_record.location_id,
                    last_access_record.offset,
                )

    return merged_regions


def update_field_target_size(command_state: CommandState, location_id: Path, pos: int):
    target_size_dict = command_state.field_target_size

    if location_id not in target_size_dict:
        target_size_dict[location_id] = pos
        return

    cur_target_size = target_size_dict[location_id]
    if cur_target_size >= pos:
        return

    target_size_dict[location_id] = pos


def fill_partial_copy_fields(command_state: CommandState, syscall_idx: int, trace: SSyscall) -> bool:
    logger = getLogger(__name__)

    command = command_state.command
    logger.info(
        "Filling partial copy fields for command %s, syscall index %d...",
        command.command_name,
        syscall_idx,
    )

    target_syscall = command.syscalls[syscall_idx]
    in_mem_last_access = [x.addr for x in trace.in_mems]
    in_mem_last_access_record: list[RecordLocation | None] = [None for _ in range(len(trace.in_mems))]

    for idx, arg in enumerate(target_syscall.arguments):
        if arg.arg_type == ArgumentType.VAR:
            arg_bytes = int.to_bytes(trace.args[idx], 8, "little")
            for field, record_location in arg.field_map.items():
                if field.size is None:
                    logger.debug(
                        "Skipping syscall_%d[%d] as it is marked as full copy...", trace.sysnum, idx
                    )
                    continue

                record_field = bytearray(command.all_fields[record_location.location_id])
                for i in range(field.size):
                    record_field[record_location.offset + i] = arg_bytes[field.offset + i]
                logger.debug(
                    "Filling %s[%d:%d] with syscall_%d[%d][%d:%d] to %s...",
                    record_location.location_id,
                    record_location.offset,
                    record_location.offset + field.size,
                    trace.sysnum,
                    idx,
                    field.offset,
                    field.offset + field.size,
                    record_field[record_location.offset : record_location.offset + field.size].hex(" ", -4),
                )
                command.all_fields[record_location.location_id] = bytes(record_field)

        elif arg.arg_type == ArgumentType.MEM:
            for field, record_location in arg.field_map.items():
                if field.size is None:
                    logger.debug(
                        "Skipping syscall_%d[%d] as it is marked as full copy...", trace.sysnum, idx
                    )
                    continue
                record_field = bytearray(command.all_fields[record_location.location_id])
                target_addr = trace.args[idx] + field.offset
                found_mem = None

                for mem_idx, mem in enumerate(trace.in_mems):
                    if target_addr >= mem.addr and target_addr <= mem.addr + mem.size - field.size:
                        if in_mem_last_access[mem_idx] < target_addr + field.size:
                            in_mem_last_access[mem_idx] = target_addr + field.size
                            in_mem_last_access_record[mem_idx] = RecordLocation(
                                record_location.location_id,
                                record_location.offset + field.size,
                            )
                        found_mem = mem_idx, mem
                        logger.debug(
                            "Input memory trace 0x%x at idx %d chosen for memory address 0x%x.",
                            mem.addr,
                            mem_idx,
                            target_addr,
                        )
                        break

                if found_mem is None:
                    continue

                mem_idx, mem = found_mem
                mem_offset = target_addr - mem.addr

                for i in range(field.size):
                    record_field[record_location.offset + i] = mem.data[mem_offset + i]
                logger.debug(
                    "Filling %s[%d:%d] with syscall_%d[%d: mem][%d:%d] to %s...",
                    record_location.location_id,
                    record_location.offset,
                    record_location.offset + field.size,
                    trace.sysnum,
                    idx,
                    field.offset,
                    field.offset + field.size,
                    record_field[record_location.offset : record_location.offset + field.size].hex(" ", -4),
                )
                update_field_target_size(
                    command_state, record_location.location_id, record_location.offset + field.size
                )
                command.all_fields[record_location.location_id] = bytes(record_field)

    for _, end, last_access_addr, last_access_record in get_memory_region_access_info(
        trace, in_mem_last_access, in_mem_last_access_record
    ):
        if last_access_record is None:
            continue

        record_len = len(command.all_fields[last_access_record.location_id])
        record_position_remaining = record_len - last_access_record.offset
        extension_request = end - last_access_addr - record_position_remaining
        if extension_request <= 0:
            continue

        logger.info(
            "Extension for field %s of command %s required of size %d.",
            last_access_record.location_id,
            command.command_name,
            extension_request,
        )
        if extend_field(
            command,
            command_state.cyclic,
            last_access_record.location_id,
            extension_request,
        ):
            return False

    expected_access = len(trace.in_mems)
    actual_access = len(command_state.base_syscalls[syscall_idx].in_mems)
    if actual_access < expected_access:
        if actual_access <= command_state.mem_access_trial:
            logger.warning(
                "Input filter bypass trial failed for %s: %d accesses were done before and accessed %d times now.",
                command.command_name,
                expected_access,
                actual_access,
            )
            # No infinite loop
            command_state.mem_access_trial = 0
            return True

        command_state.mem_access_trial = actual_access
        logger.info(
            "Input filter detected for %s: %d accesses were expected, but accessed %d times.",
            command.command_name,
            expected_access,
            actual_access,
        )
        return False

    command_state.mem_access_trial = 0
    return True


def fill_full_copy_fields(command_state: CommandState, syscall_idx: int, trace: SSyscall):
    logger = getLogger(__name__)

    command = command_state.command
    logger.info(
        "Filling full copy fields for command %s, syscall index %d...",
        command.command_name,
        syscall_idx,
    )

    target_syscall = command.syscalls[syscall_idx]

    for idx, arg in enumerate(target_syscall.arguments):
        if arg.arg_type == ArgumentType.MEM:
            arg_offset = 0
            for field, record_location in sorted(arg.field_map.items(), key=lambda x: x[0].offset):
                if field.size is not None:
                    continue

                record_id = record_location.location_id
                target_addr = trace.args[idx] + field.offset + arg_offset
                found_mem = None

                for mem_idx, mem in enumerate(trace.in_mems):
                    if target_addr >= mem.addr and target_addr <= mem.addr + mem.size:
                        found_mem = mem_idx, mem
                        logger.debug(
                            "Input memory trace 0x%x at idx %d chosen for memory address 0x%x.",
                            mem.addr,
                            mem_idx,
                            target_addr,
                        )
                        break

                if found_mem is None:
                    continue

                mem_idx, mem = found_mem
                mem_offset = target_addr - mem.addr

                new_data = None

                # No extension availability check as it has been already done in full copy detection
                if field.insert:
                    new_data = mem.data[mem_offset:]
                    null_byte_pos = new_data.find(b"\x00")
                    if null_byte_pos == -1:
                        logger.warning(
                            "syscall_%d[%d][%d:] marked as inserted data but cannot find NULL terminator.",
                            trace.sysnum,
                            mem_idx,
                            field.offset + arg_offset,
                        )
                        continue

                    new_data = new_data[: null_byte_pos + 1]
                else:
                    new_data = mem.data[mem_offset:]

                logger.debug(
                    "Filling %s[%d:%d] with syscall_%d[%d: mem][%d:%d] to %s...",
                    record_id,
                    record_location.offset,
                    record_location.offset + len(new_data),
                    trace.sysnum,
                    idx,
                    field.offset + arg_offset,
                    field.offset + arg_offset + len(new_data),
                    new_data.hex(" ", -4),
                )
                original_size = len(command.all_fields[record_id])
                new_size = len(new_data)
                size_diff = new_size - original_size

                size_id = command.size_constraints[record_id]
                size_field = command.all_fields[size_id]
                new_size_bytes = int.to_bytes(new_size, len(size_field), "little")

                command.all_fields[record_id] = new_data
                command.all_fields[size_id] = new_size_bytes
                logger.debug(
                    "Updating size constraint %s of %s with new length %d...",
                    size_id,
                    record_id,
                    new_size,
                )

                new_field = dataclasses.replace(field, offset=field.offset + arg_offset)
                arg.field_map.pop(field)
                arg.field_map[new_field] = record_location
                aligned_diff = size_diff + (-size_diff % 4)

                logger.debug(
                    "Updating syscall_%d[%d: mem] shift offset from %d to %d...",
                    trace.sysnum,
                    idx,
                    arg_offset,
                    arg_offset + aligned_diff,
                )

                arg_offset += aligned_diff
