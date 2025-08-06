from logging import getLogger
from pathlib import Path
from typing import Generator

from .blob import generate_blob_one
from .lib import SSyscall, TestLang, TTokens
from .mimic.fill import compilance_diff, fill_full_copy_fields, fill_partial_copy_fields
from .mimic.one import get_command_template, update_command_template
from .template.extend import command_fit_field_size
from .trace.diff import target_trace_coverage


def reproduce_blob(
    target_trace: list[SSyscall], harness: Path, syntax_parsed: TestLang
) -> Generator[bytes, None, None]:
    logger = getLogger(__name__)

    template = get_command_template(syntax_parsed, harness, TTokens.INPUT)

    while True:
        trace_coverage, _, start, end = target_trace_coverage(
            target_trace,
            template.base_syscalls,
            template.command.syscalls,
            compilance_diff,
        )

        if start is None or end is None:
            return

        template.field_target_size = dict()
        rerun_required = False
        for syscall_idx, trace in trace_coverage:
            fill_full_copy_fields(template, syscall_idx, trace)

            while not fill_partial_copy_fields(template, syscall_idx, trace):
                logger.info(
                    "Filling algorithm required additional detection iteration for command %s syscall index %d.",
                    template.command.command_name,
                    syscall_idx,
                )
                rerun_required = update_command_template(template, harness) or rerun_required

            rerun_required = update_command_template(template, harness) or rerun_required

            logger.info(
                "Command %s filling done for syscall_%d.",
                template.command.command_name,
                trace.sysnum,
            )

        if rerun_required:
            continue

        out = generate_blob_one(command_fit_field_size(template.command, template.field_target_size))
        logger.debug("Reproduction trial: %s", out.hex(" ", -4))
        yield out
        break
    return
