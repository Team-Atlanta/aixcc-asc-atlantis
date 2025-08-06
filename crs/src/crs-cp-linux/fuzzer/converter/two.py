from logging import getLogger
from pathlib import Path
from typing import Generator

from .blob import generate_blob_two
from .lib import SSyscall, TestLang
from .mimic import CommandState
from .mimic.fill import compilance_diff, fill_full_copy_fields, fill_partial_copy_fields
from .mimic.two import get_command_templates, get_target_trace, update_command_template
from .template import Command
from .template.extend import command_fit_field_size
from .trace.diff import target_trace_coverage


def range_challenge(a: tuple[int, int], b: tuple[int, int]) -> bool | None:
    a_start, a_end = a
    b_start, b_end = b

    if a_end <= b_start:
        return False
    elif b_end <= a_start:
        return True
    else:
        return None


def reproduce_blob(
    poc_trace: list[SSyscall], harness: Path, syntax_parsed: TestLang
) -> Generator[bytes, None, None]:
    logger = getLogger(__name__)

    target_trace, blank_trace = get_target_trace(poc_trace, harness)
    templates = get_command_templates(syntax_parsed, harness, blank_trace)

    def reproduce_syscalls(
        target_trace: list[SSyscall],
        command_states: dict[str, CommandState],
        commands: list[Command] | None = None,
    ) -> Generator[bytes, None, None]:
        if commands is None:
            commands = list()

        if len(target_trace) == 0:
            if len(commands) == 0:
                return
            out = generate_blob_two(syntax_parsed, commands)
            logger.debug("Reproduction trial: %s", out.hex(" ", -4))
            yield out

        trial_order = list()
        coverage_area = dict()
        trace_coverages = dict()
        left_traces = dict()

        for command_name in command_states:
            command_state = command_states[command_name]
            trace_coverage, left_trace, start, end = target_trace_coverage(
                target_trace,
                command_state.base_syscalls,
                command_state.command.syscalls,
                compilance_diff,
            )

            if start is None or end is None:
                continue

            this_coverage_area = start, end
            skip = False
            removal = list()
            for champion in trial_order:
                challenge = range_challenge(coverage_area[champion], this_coverage_area)
                if challenge is None:
                    pass
                elif challenge:
                    removal.append(champion)
                else:
                    skip = True
                    break

            if skip:
                continue

            for target in removal:
                trial_order.remove(target)

            trial_order.append(command_name)
            coverage_area[command_name] = this_coverage_area
            trace_coverages[command_name] = trace_coverage
            left_traces[command_name] = left_trace

        if len(trial_order) == 0:
            if len(commands) == 0:
                return
            out = generate_blob_two(syntax_parsed, commands)
            logger.debug("Reproduction trial: %s", out.hex(" ", -4))
            yield out

        trial_order.sort(key=lambda x: coverage_area[x])

        for command_name in trial_order:
            _, end = coverage_area[command_name]
            trace_coverage = trace_coverages[command_name]
            command_state = command_states[command_name]

            command_state.field_target_size = dict()
            rerun_required = False
            for syscall_idx, trace in trace_coverage:
                fill_full_copy_fields(command_state, syscall_idx, trace)
                while not fill_partial_copy_fields(command_state, syscall_idx, trace):
                    logger.info(
                        "Filling algorithm required additional detection iteration for command %s syscall index %d.",
                        command_state.command.command_name,
                        syscall_idx,
                    )
                    rerun_required = (
                        update_command_template(syntax_parsed, command_state, harness, blank_trace)
                        or rerun_required
                    )
                rerun_required = (
                    update_command_template(syntax_parsed, command_state, harness, blank_trace)
                    or rerun_required
                )

                logger.info(
                    "Command %s filling done for syscall_%d.",
                    command_state.command.command_name,
                    trace.sysnum,
                )

            if rerun_required:
                yield from reproduce_syscalls(target_trace, command_states, commands)
                return

            commands.append(command_fit_field_size(command_state.command, command_state.field_target_size))
            yield from reproduce_syscalls(left_traces[command_name], command_states, commands)
            commands.pop()

    yield from reproduce_syscalls(target_trace, templates)
