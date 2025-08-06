import string
from copy import deepcopy
from logging import getLogger
from pathlib import Path

from pwnlib.util.cyclic import cyclic_gen

from ..blob import generate_blob_two
from ..lib import SSyscall, TestLang, TTokens
from ..template import ArgumentType, RecordLocation
from ..template.generate import generate_command_template, prepare_command_syscall, prepare_command_syscalls
from ..trace import generate_trace_harness
from ..trace.diff import diff_is_similar_weak, diff_trace, diff_zip
from . import CommandState
from .detect.constant import detect_constant_field
from .detect.copy import (
    FieldPointer,
    detect_byte_copy_field,
    detect_full_copy_field,
    detect_partial_copy_field,
    generate_full_copy_diff_command,
)
from .detect.external import detect_external_field


## IDEA: filter out unnecessary traces by getting syscalls not covered when
##       0 commands are passed into harness
def get_target_trace(poc_trace: list[SSyscall], harness: Path) -> tuple[list[SSyscall], list[SSyscall]]:
    logger = getLogger(__name__)

    logger.info("Preparing target trace...")
    logger.info("Tracing blank Harness...")
    plain = generate_trace_harness(harness, b"\x00\x00\x00\x00")

    if plain is None:
        logger.error("Trace failed while composing target trace.")
        raise Exception("Trace failed while composing target trace.")

    diff_result = diff_trace(poc_trace, plain)

    target = list(map(lambda x: x[1], diff_result.base_only))
    blank_harness = list(map(lambda x: x[1], sorted(diff_result.common + diff_result.target_only)))

    logger.info("Target trace composition done with length %d.", len(target))
    logger.info("Blank harness trace composition done with length %d.", len(blank_harness))

    return target, blank_harness


def perform_byte_copy_detection(syntax: TestLang, harness: Path, command_state: CommandState):
    logger = getLogger(__name__)
    if command_state.byte_mapping_targets == set():
        return

    command = deepcopy(command_state.command)
    base_syscalls = command_state.base_syscalls
    mapping_targets = command_state.byte_mapping_targets
    mapping_candidates: dict[RecordLocation, set[FieldPointer]] = dict()

    for byte_trial_start in range(4):
        trial_map: dict[RecordLocation, int] = dict()
        for i, record_location in enumerate(mapping_targets):
            byte_trial = (byte_trial_start + i) % 0x100
            field_bytes = bytearray(command.all_fields[record_location.location_id])
            field_bytes[record_location.offset] = byte_trial
            command.all_fields[record_location.location_id] = bytes(field_bytes)
            trial_map[record_location] = byte_trial

        byte_copy_blob = generate_blob_two(syntax, [command])
        byte_copy_trace = generate_trace_harness(harness, byte_copy_blob)

        if byte_copy_trace is None:
            logger.error("Trace failed while preparing command template.")
            raise Exception("Trace failed while preparing command template.")

        syscalls: list[SSyscall | None] = list()
        trace_zip = diff_zip(base_syscalls, byte_copy_trace, diff_is_similar_weak)
        for syscall_base, syscall_copy in trace_zip:
            if syscall_base is None:
                continue
            syscalls.append(syscall_copy)

        detect_byte_copy_field(command, trial_map, syscalls, mapping_candidates)

    mapped_location = set()
    for record_location, field_pointers in mapping_candidates.items():
        is_empty = True
        for field_pointer in field_pointers:
            is_empty = False
            syscall_i = field_pointer.syscall_idx
            syscall = command_state.command.syscalls[syscall_i]
            idx = field_pointer.arg_idx
            field = field_pointer.field
            argument = syscall.arguments[idx]
            argument.field_map[field] = record_location
            if argument.arg_type == ArgumentType.MEM:
                logger.debug(
                    "Syscall entry %d: syscall_%d[%d: mem][%d:%d] marked partial copy of record field %s[%d:%d].",
                    syscall_i,
                    syscall.number,
                    idx,
                    field.offset,
                    field.offset + field.size,  # type: ignore
                    record_location.location_id,
                    record_location.offset,
                    record_location.offset + field.size,  # type: ignore
                )
            else:
                logger.debug(
                    "Syscall entry %d: syscall_%d[%d][%d:%d] marked partial copy of record field %s[%d:%d].",
                    syscall_i,
                    syscall.number,
                    idx,
                    field.offset,
                    field.offset + field.size,  # type: ignore
                    record_location.location_id,
                    record_location.offset,
                    record_location.offset + field.size,  # type: ignore
                )

        if not is_empty:
            mapped_location.add(record_location)

    command_state.byte_mapping_targets.difference_update(mapped_location)


def get_command_template(
    syntax: TestLang, harness: Path, blank_trace: list[SSyscall], command_name: str
) -> CommandState:
    logger = getLogger(__name__)
    logger.info("Generating command template for command %s.", command_name)

    command_template, cyclic = generate_command_template(syntax, command_name)
    command_template_const_check, _ = generate_command_template(
        syntax, command_name, cyclic_gen(bytes(string.ascii_uppercase, encoding="ascii")), (4, 5)
    )

    base_blob = generate_blob_two(syntax, [command_template])
    const_check_blob = generate_blob_two(syntax, [command_template_const_check])

    trace = generate_trace_harness(harness, base_blob)
    trace_external_check = generate_trace_harness(harness, base_blob, False)
    trace_const_check = generate_trace_harness(harness, const_check_blob)

    if trace is None or trace_external_check is None or trace_const_check is None:
        logger.error("Trace failed while preparing command template.")
        raise Exception("Trace failed while preparing command template.")

    trace_filtered = list(map(lambda x: x[1], diff_trace(blank_trace, trace).target_only))
    trace_external_check_filtered = list(
        map(lambda x: x[1], diff_trace(blank_trace, trace_external_check).target_only)
    )
    trace_const_check_filtered = list(
        map(lambda x: x[1], diff_trace(blank_trace, trace_const_check).target_only)
    )

    prepare_command_syscalls(command_template, trace_filtered)
    logger.debug("Base template generated.")

    external_zip = diff_zip(trace_filtered, trace_external_check_filtered, diff_is_similar_weak)
    const_zip = diff_zip(trace_filtered, trace_const_check_filtered, diff_is_similar_weak)

    detect_external_field(command_template, external_zip)
    detect_constant_field(command_template, const_zip)

    blacklist = set()
    for record_id in command_template.all_fields:
        if record_id in command_template.size_fields:
            logger.debug("No full copy check for %s as it is a size field.", record_id)
            continue

        if record_id not in command_template.size_constraints:
            logger.debug("No full copy check for %s as it has literal size constraint.", record_id)
            continue

        size_id = command_template.size_constraints[record_id]
        if size_id in command_template.constants:
            logger.debug("No full copy check for %s as it has constant size constraint.", record_id)
            continue

        diff_command = generate_full_copy_diff_command(command_template, record_id)
        diff_blob = generate_blob_two(syntax, [diff_command])
        diff_check = generate_trace_harness(harness, diff_blob)

        if diff_check is None:
            logger.error("Trace failed while preparing full copy check. Skipping this record field...")
            continue

        diff_check_filtered = list(map(lambda x: x[1], diff_trace(blank_trace, diff_check).target_only))
        diff_trace_zip = diff_zip(trace_filtered, diff_check_filtered, diff_is_similar_weak)
        if detect_full_copy_field(command_template, record_id, diff_trace_zip):
            blacklist.add(record_id)

    byte_mapping_targets: set[RecordLocation] = set()
    for record_id in command_template.all_fields:
        if (
            record_id in command_template.size_fields
            or record_id in command_template.size_constraints
            or record_id in command_template.constants
        ):
            continue

        record_size = len(command_template.all_fields[record_id])
        for i in range(record_size):
            byte_mapping_targets.add(RecordLocation(record_id, i))

    marked_targets = detect_partial_copy_field(command_template, cyclic, trace_filtered, blacklist)
    command_state = CommandState(
        command_template,
        cyclic,
        trace_filtered,
        blacklist,
        dict(),
        byte_mapping_targets.difference(marked_targets),
        0,
    )

    perform_byte_copy_detection(syntax, harness, command_state)
    return command_state


def update_command_template(
    syntax: TestLang,
    command_state: CommandState,
    harness: Path,
    blank_trace: list[SSyscall],
):
    logger = getLogger(__name__)
    command_name = command_state.command.command_name
    logger.info("Updating command template for command %s.", command_name)

    base_blob = generate_blob_two(syntax, [command_state.command])

    trace = generate_trace_harness(harness, base_blob)
    if trace is None:
        logger.error("Trace failed while preparing command template.")
        raise Exception("Trace failed while preparing command template.")

    trace_filtered = list(map(lambda x: x[1], diff_trace(blank_trace, trace).target_only))

    base_zip = diff_zip(command_state.base_syscalls, trace_filtered, diff_is_similar_weak)

    new_base_syscalls = []
    extended = False
    for idx, (syscall_a, syscall_b) in enumerate(base_zip):
        if syscall_b is None:
            new_base_syscalls.append(syscall_a)
        elif syscall_a is None:
            new_syscall_entry = prepare_command_syscall(syscall_b)
            command_state.command.syscalls.insert(idx, new_syscall_entry)
            new_base_syscalls.append(syscall_b)
            extended = True
        else:
            new_base_syscalls.append(syscall_b)

    logger.debug(
        "Command template base syscalls updated from length %d to %d.",
        len(command_state.base_syscalls),
        len(new_base_syscalls),
    )
    command_state.base_syscalls = new_base_syscalls

    # TODO: do full copy detection
    marked_targets = detect_partial_copy_field(
        command_state.command, command_state.cyclic, new_base_syscalls, command_state.full_copy_fields
    )
    command_state.byte_mapping_targets.difference_update(marked_targets)
    perform_byte_copy_detection(syntax, harness, command_state)
    return extended


def get_command_templates(
    syntax: TestLang, harness: Path, blank_trace: list[SSyscall]
) -> dict[str, CommandState]:
    logger = getLogger(__name__)

    logger.info("Starting command template generation procedure...")

    # We consider INPUT has test_lang format (see ../reverser/README.md)
    if TTokens.INPUT not in syntax.records:
        logger.error("%s must be present in syntax record.", TTokens.INPUT)
        raise Exception(f"{TTokens.INPUT} must be present in syntax record.")

    if "COMMAND" not in syntax.records:
        logger.error("COMMAND must be present in syntax record.")
        raise Exception("COMMAND must be present in syntax record.")
    cmd_record = syntax.records["COMMAND"]

    templates = dict()
    target_records = list(map(lambda x: x.name, cmd_record.fields))
    for target_record in target_records:
        template = get_command_template(syntax, harness, blank_trace, target_record)
        templates[target_record] = template

    return templates
