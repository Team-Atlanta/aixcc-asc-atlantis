import random
import struct
from logging import getLogger
from pathlib import Path

from pwnlib.util.cyclic import cyclic_gen

from ..lib import SSyscall, TestLang, TField, TRecord, TTokens
from . import Argument, ArgumentType, Command, RecordLocation, Syscall


def check_circular_dependency(scope: Path, record_name: str) -> bool:
    while scope != scope.parent:
        if scope.name == record_name:
            return True
        scope = scope.parent

    return False


def lookup_effective_field(scope: Path, field_name: str, field_set: set, local_only=False) -> Path:
    logger = getLogger(__name__)
    found = False

    while scope != scope.parent:
        full_field_name = scope / field_name

        if full_field_name in field_set:
            logger.debug(
                "Resolved effective field %s with full name of %s.",
                field_name,
                full_field_name,
            )
            found = True

        if found or local_only:
            break

        scope = scope.parent

    if not found:
        logger.error("Tried referencing %s from scope %s but not defined yet.", field_name, str(scope))
        raise Exception(f"Tried referencing {field_name} from scope {scope} but not defined yet.")

    return scope / field_name


def lookup_value(scope: Path, command: Command, field_name: str, local_only=False) -> tuple[bytes, Path]:
    logger = getLogger(__name__)
    concrete_value = None

    while scope != scope.parent:
        full_field_name = scope / field_name
        concrete_value = None

        if full_field_name in command.all_fields:
            concrete_value = command.all_fields[full_field_name]
            logger.debug(
                "Resolved field %s with full name of %s with value %s.",
                field_name,
                full_field_name,
                concrete_value.hex(" ", -4),
            )

        if local_only or concrete_value:
            break
        scope = scope.parent

    if not concrete_value:
        logger.error("Tried referencing %s from scope %s but not defined yet.", field_name, str(scope))
        raise Exception(f"Tried referencing {field_name} from scope {scope} but not defined yet.")

    return concrete_value, scope / field_name


def lookup_int_value(scope: Path, command: Command, field_name: str, local_only=False) -> tuple[int, Path]:
    byte_value, full_name = lookup_value(scope, command, field_name, local_only)
    return int.from_bytes(byte_value, "little"), full_name


def generate_value(
    scope: Path,
    command: Command,
    cyclic: cyclic_gen,
    field_name: str,
    size: int,
    size_field: Path | None = None,
    start_end: tuple[int, int] | None = None,
):
    logger = getLogger(__name__)
    full_field_name = scope / field_name
    if start_end is not None:
        start, end = start_end
        value = random.randrange(start, end) * 4
        logger.debug(
            "Value %d generated with range (%d, %d) * 4 for %s.", value, start, end, full_field_name
        )
        command.all_fields[full_field_name] = value.to_bytes(size, "little")
    else:
        full_cyclic = b""
        for off in range(0, size, 4):
            real_size = min(4, size - off - 1)
            new_cyclic = cyclic.get(4)

            if not isinstance(new_cyclic, bytes):
                raise Exception("Cyclic generator gave broken output")

            logger.debug("Value %s generated for %s.", new_cyclic.hex(), full_field_name)

            if real_size == 4:
                full_cyclic += new_cyclic
            else:
                full_cyclic += new_cyclic[:real_size] + b"\x00"

            command.cyclic_map.append((RecordLocation(full_field_name, off), real_size))
        command.all_fields[full_field_name] = full_cyclic

    if size_field is not None:
        logger.debug("Size constraint set for %s: %s", full_field_name, size_field)
        command.size_constraints[full_field_name] = size_field

    return command.all_fields[full_field_name]


def generate_command_template(
    syntax: TestLang,
    command_name: str,
    cyclic: cyclic_gen | None = None,
    size_range: tuple[int, int] = (8, 9),
) -> tuple[Command, cyclic_gen]:
    logger = getLogger(__name__)
    command = Command(command_name, list(), dict(), set(), dict(), set(), list(), list())
    if cyclic is None:
        cyclic = cyclic_gen()

    logger.info("Generating template of %s...", command_name)

    current_scope = Path(".")
    field_set = set()
    def identify_size_fields(record_name: str):
        nonlocal current_scope
        nonlocal field_set
        saved_scope = current_scope
        current_scope = current_scope / record_name
        try:
            records = syntax.records
            if record_name not in records:
                logger.error('Syntax error: no record name "%s" found.', command_name)
                raise Exception(f'Syntax error: no record name "{command_name}" found.')

            logger.debug("Entering record: %s", record_name)
            target_record = records[record_name]

            if target_record.type == TRecord.UNION:
                raise Exception("Unimplemented, yet.")
            # Possible BUG: in test_lang there is no SEQ type updated
            else:
                for field_idx, field in enumerate(target_record.fields):
                    logger.debug("Entering field: %s", field.name)
                    if field.type == TField.Normal:
                        # "size" must exist in field attributes
                        size = field.attrs[TTokens.SIZE]
                        if isinstance(size, str):
                            size_field = lookup_effective_field(current_scope, size, field_set)
                            command.size_fields.add(size_field)
                        field_set.add(current_scope / field.name)

                    elif field.type == TField.Record:
                        if check_circular_dependency(current_scope, field.name):
                            logger.error("Circular dependency detected! Stopping here...")
                            raise Exception("Circular dependency detected! Stopping here...")

                        saved_scope_field = current_scope
                        current_scope = current_scope / str(field_idx)
                        try:
                            logger.debug("Field position %d: %s", field_idx, field.name)
                            identify_size_fields(field.name)
                        finally:
                            current_scope = saved_scope_field

                    elif field.type == TField.Array:
                        # "cnt" always in field.attrs due to Field.check_attrs()
                        cnt = field.attrs[TTokens.CNT]
                        if isinstance(cnt, str):
                            size_field = lookup_effective_field(current_scope, cnt, field_set)
                            command.size_fields.add(size_field)

                        # TODO: This is a workaround
                        for i in range(size_range[1] - 1):
                            saved_scope_arr = current_scope
                            current_scope = current_scope / str(i)
                            try:
                                logger.debug("Entering element #%d", i)
                                identify_size_fields(field.name)
                            finally:
                                current_scope = saved_scope_arr
        finally:
            current_scope = saved_scope


    def add_record_locations(record_name: str):
        nonlocal current_scope
        saved_scope = current_scope
        current_scope = current_scope / record_name
        try:
            records = syntax.records
            if record_name not in records:
                logger.error('Syntax error: no record name "%s" found.', command_name)
                raise Exception(f'Syntax error: no record name "{command_name}" found.')

            logger.debug("Entering record: %s", record_name)
            target_record = records[record_name]

            if target_record.type == TRecord.UNION:
                raise Exception("Unimplemented, yet.")
            # Possible BUG: in test_lang there is no SEQ type updated
            else:
                for field_idx, field in enumerate(target_record.fields):
                    logger.debug("Entering field: %s", field.name)
                    if field.type == TField.Normal:
                        # "size" must exist in field attributes
                        if TTokens.VALUE in field.attrs:
                            size = field.attrs[TTokens.SIZE]
                            if isinstance(size, str):
                                logger.warn(
                                    "Concrete defined value uses symbolic size attribute in %s. Is it intended?",
                                    field.name,
                                )
                                size, _ = lookup_int_value(current_scope, command, size)
                            elif not isinstance(size, int):
                                logger.error(
                                    "Unexpected attr type of %s for field %s.", TTokens.SIZE, field.name
                                )
                                raise Exception(
                                    f"Unexpected attr type of {TTokens.SIZE} for field {field.name}."
                                )

                            value = field.attrs[TTokens.VALUE]
                            full_record_name = current_scope / field.name
                            command.serialization_order.append(full_record_name)
                            if isinstance(value, int):
                                command.all_fields[full_record_name] = value.to_bytes(size, "little")
                            else:
                                command.all_fields[full_record_name] = struct.pack(f"<{size}s", value)

                            command.constants.add(full_record_name)

                            logger.debug(
                                "Field %s set with concrete value %d of size %d.",
                                field.name,
                                value,
                                size,
                            )
                        else:
                            size = field.attrs[TTokens.SIZE]
                            size_field = None

                            if isinstance(size, str):
                                size, size_field = lookup_int_value(current_scope, command, size)
                            elif not isinstance(size, int):
                                logger.error(
                                    "Unexpected attr type of %s for field %s.", TTokens.SIZE, field.name
                                )
                                raise Exception(
                                    f"Unexpected attr type of {TTokens.SIZE} for field {field.name}."
                                )

                            def check_size_metadata(full_record_name):
                                return full_record_name in command.size_fields

                            full_record_name = current_scope / field.name
                            command.serialization_order.append(full_record_name)
                            random_range = size_range if check_size_metadata(full_record_name) else None
                            value = generate_value(
                                current_scope,
                                command,
                                cyclic,
                                field.name,
                                size,
                                size_field,
                                random_range,
                            )
                            logger.debug(
                                "Field %s set with generated value of size %d.",
                                field.name,
                                size,
                            )
                            if size_field is not None:
                                logger.debug("--> size constraint bound: %s", size_field)

                    elif field.type == TField.Record:
                        if check_circular_dependency(current_scope, field.name):
                            logger.error("Circular dependency detected! Stopping here...")
                            raise Exception("Circular dependency detected! Stopping here...")

                        saved_scope_field = current_scope
                        current_scope = current_scope / str(field_idx)
                        try:
                            logger.debug("Field position %d: %s", field_idx, field.name)
                            add_record_locations(field.name)
                        finally:
                            current_scope = saved_scope_field

                    elif field.type == TField.Array:
                        # "cnt" always in field.attrs due to Field.check_attrs()
                        cnt = field.attrs[TTokens.CNT]
                        if isinstance(cnt, str):
                            cnt, _ = lookup_int_value(current_scope, command, cnt)
                        elif not isinstance(cnt, int):
                            logger.error(
                                "Unexpected attr type of %s for field %s.", TTokens.SIZE, field.name
                            )
                            raise Exception(
                                f"Unexpected attr type of {TTokens.CNT} for field {field.name}."
                            )

                        logger.debug("--> Array with length %d", cnt)

                        for i in range(cnt):
                            saved_scope_arr = current_scope
                            current_scope = current_scope / str(i)
                            try:
                                logger.debug("Entering element #%d", i)
                                add_record_locations(field.name)
                            finally:
                                current_scope = saved_scope_arr

                        # TODO: Support array size control
        finally:
            current_scope = saved_scope

    identify_size_fields(command_name)
    current_scope = Path(".")
    add_record_locations(command_name)

    logger.info("Generation result:")
    for path, data in command.all_fields.items():
        logger.info("    - %s: %s", path, data.hex(" ", -4))

    return command, cyclic


def prepare_command_syscall(syscall: SSyscall):
    syscall_entry = Syscall(
        syscall.sysnum,
        [Argument(ArgumentType.UNKNOWN, dict()) for _ in range(syscall.argc)],
    )
    return syscall_entry


def prepare_command_syscalls(command: Command, syscalls: list[SSyscall]):
    for syscall in syscalls:
        command.syscalls.append(prepare_command_syscall(syscall))
