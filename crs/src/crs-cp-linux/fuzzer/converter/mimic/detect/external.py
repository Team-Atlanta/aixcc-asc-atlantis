from logging import getLogger

from ...lib import SSyscall
from ...template import ArgumentType, Command


def detect_external_field(
    command: Command, syscall_diff_zip: list[tuple[SSyscall | None, SSyscall | None]]
):
    logger = getLogger(__name__)
    logger.info("Performing external field detection on command %s...", command.command_name)

    offset = 0
    mark_count = 0
    for syscall_i, (syscall_a, syscall_b) in enumerate(syscall_diff_zip):
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

        for idx, (arg_a, arg_b) in enumerate(zip(syscall_a.args, syscall_b.args)):
            if arg_a == arg_b:
                continue

            is_mem = False
            for syscall_a_mem in syscall_a.in_mems:
                if syscall_a_mem.addr == arg_a:
                    is_mem = True
                    break

            if is_mem:
                continue

            for syscall_b_mem in syscall_b.in_mems:
                if syscall_b_mem.addr == arg_b:
                    is_mem = True
                    break

            if is_mem:
                continue

            logger.debug(
                "Syscall entry %d: syscall_%d[%d] marked as external. (0x%x != 0x%x)",
                syscall_i + offset,
                syscall_a.sysnum,
                idx,
                arg_a,
                arg_b,
            )
            logger.debug(
                "Syscall entry %d argument index %d marked as external.",
                syscall_i + offset,
                idx,
            )
            syscall_entry.arguments[idx].arg_type = ArgumentType.EXTERN
            mark_count += 1

    logger.info("Total %d arguments marked as external for command %s.", mark_count, command.command_name)
