from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from typing import Callable

from ..lib import SSyscall
from ..template import Syscall


class DiffTrack(Enum):
    REWIND_BASE = 1
    REWIND_TARGET = 2
    MATCH = 3


@dataclass
class TraceDiffResult:
    common: list[tuple[int, SSyscall]]
    base_only: list[tuple[int, SSyscall]]
    target_only: list[tuple[int, SSyscall]]


def diff_is_similar_weak(a: SSyscall, b: SSyscall) -> bool:
    return a.sysnum == b.sysnum and a.argc == b.argc


def diff_is_similar(a: SSyscall, b: SSyscall) -> bool:
    if a.sysnum != b.sysnum or a.argc != b.argc:
        return False

    left_mem = dict()
    right_mem = dict()

    for mem in a.in_mems + a.out_mems:
        if mem.addr not in left_mem:
            left_mem[mem.addr] = mem.data

    for mem in b.in_mems + b.out_mems:
        if mem.addr not in right_mem:
            right_mem[mem.addr] = mem.data

    for i in range(a.argc):
        left = a.args[i]
        right = b.args[i]

        if left in left_mem and right in right_mem:
            continue

        if left != right:
            return False

    return True


def target_trace_coverage(
    base_trace: list[SSyscall],
    trace: list[SSyscall],
    template_syscall: list[Syscall],
    comparator: Callable[[SSyscall, SSyscall, Syscall], bool],
) -> tuple[list[tuple[int, SSyscall]], list[SSyscall], int | None, int | None]:
    logger = getLogger(__name__)

    base_len = len(base_trace)
    target_len = len(trace)

    trace_coverage = []
    left_trace = []

    diff_count = [[0] * (target_len + 1) for _ in range(base_len + 1)]
    diff_track = [
        [DiffTrack.REWIND_BASE] + ([DiffTrack.REWIND_TARGET] * (target_len)) for _ in range(base_len + 1)
    ]

    logger.debug("Finding trace coverage...")

    for i in range(base_len):
        for j in range(target_len):
            if comparator(base_trace[i], trace[j], template_syscall[j]):
                diff_count[i + 1][j + 1] = diff_count[i][j] + 1
                if diff_count[i + 1][j + 1] == diff_count[i][j + 1]:
                    diff_track[i + 1][j + 1] = DiffTrack.REWIND_BASE
                elif diff_count[i + 1][j + 1] == diff_count[i + 1][j]:
                    diff_track[i + 1][j + 1] = DiffTrack.REWIND_TARGET
                else:
                    diff_track[i + 1][j + 1] = DiffTrack.MATCH
            elif diff_count[i][j + 1] < diff_count[i + 1][j]:
                diff_count[i + 1][j + 1] = diff_count[i + 1][j]
                diff_track[i + 1][j + 1] = DiffTrack.REWIND_TARGET
            else:
                diff_count[i + 1][j + 1] = diff_count[i][j + 1]
                diff_track[i + 1][j + 1] = DiffTrack.REWIND_BASE

    base_cursor = base_len
    target_cursor = target_len

    start_pos = None
    end_pos = None

    while base_cursor > 0 or target_cursor > 0:
        if diff_track[base_cursor][target_cursor] == DiffTrack.MATCH:
            logger.debug("MATCH: base %d == target %d", base_cursor - 1, target_cursor - 1)
            trace_coverage.append((target_cursor - 1, base_trace[base_cursor - 1]))
            if end_pos is None:
                end_pos = base_cursor  # Exclusive end
            start_pos = base_cursor - 1
            base_cursor -= 1
            target_cursor -= 1
        elif diff_track[base_cursor][target_cursor] == DiffTrack.REWIND_BASE:
            left_trace.append(base_trace[base_cursor - 1])
            base_cursor -= 1
        elif diff_track[base_cursor][target_cursor] == DiffTrack.REWIND_TARGET:
            target_cursor -= 1
        else:
            raise Exception("Unreachable")

    trace_coverage.reverse()
    left_trace.reverse()
    logger.debug("Trace coverage discovery done.")

    return trace_coverage, left_trace, start_pos, end_pos


def diff_trace(
    base_trace: list[SSyscall],
    trace: list[SSyscall],
    comparator: Callable[[SSyscall, SSyscall], bool] = diff_is_similar,
) -> TraceDiffResult:
    base_len = len(base_trace)
    target_len = len(trace)

    common = []
    base_only = []
    target_only = []

    diff_count = [[0] * (target_len + 1) for _ in range(base_len + 1)]
    diff_track = [
        [DiffTrack.REWIND_BASE] + ([DiffTrack.REWIND_TARGET] * (target_len)) for _ in range(base_len + 1)
    ]

    for i in range(base_len):
        for j in range(target_len):
            if comparator(base_trace[i], trace[j]):
                diff_count[i + 1][j + 1] = diff_count[i][j] + 1
                diff_track[i + 1][j + 1] = DiffTrack.MATCH
            elif diff_count[i][j + 1] < diff_count[i + 1][j]:
                diff_count[i + 1][j + 1] = diff_count[i + 1][j]
                diff_track[i + 1][j + 1] = DiffTrack.REWIND_TARGET
            else:
                diff_count[i + 1][j + 1] = diff_count[i][j + 1]
                diff_track[i + 1][j + 1] = DiffTrack.REWIND_BASE

    base_cursor = base_len
    target_cursor = target_len

    seq = 0
    while base_cursor > 0 or target_cursor > 0:
        if diff_track[base_cursor][target_cursor] == DiffTrack.MATCH:
            common.append((seq, base_trace[base_cursor - 1]))
            seq -= 1
            base_cursor -= 1
            target_cursor -= 1
        elif diff_track[base_cursor][target_cursor] == DiffTrack.REWIND_BASE:
            base_only.append((seq, base_trace[base_cursor - 1]))
            seq -= 1
            base_cursor -= 1
        elif diff_track[base_cursor][target_cursor] == DiffTrack.REWIND_TARGET:
            target_only.append((seq, trace[target_cursor - 1]))
            seq -= 1
            target_cursor -= 1
        else:
            raise Exception("Unreachable")

    common.reverse()
    base_only.reverse()
    target_only.reverse()

    return TraceDiffResult(common, base_only, target_only)


def diff_zip(
    base_trace: list[SSyscall],
    trace: list[SSyscall],
    comparator: Callable[[SSyscall, SSyscall], bool] = diff_is_similar,
) -> list[tuple[SSyscall | None, SSyscall | None]]:
    base_len = len(base_trace)
    target_len = len(trace)

    result = list()

    diff_count = [[0] * (target_len + 1) for _ in range(base_len + 1)]
    diff_track = [
        [DiffTrack.REWIND_BASE] + ([DiffTrack.REWIND_TARGET] * (target_len)) for _ in range(base_len + 1)
    ]

    for i in range(base_len):
        for j in range(target_len):
            if comparator(base_trace[i], trace[j]):
                diff_count[i + 1][j + 1] = diff_count[i][j] + 1
                diff_track[i + 1][j + 1] = DiffTrack.MATCH
            elif diff_count[i][j + 1] < diff_count[i + 1][j]:
                diff_count[i + 1][j + 1] = diff_count[i + 1][j]
                diff_track[i + 1][j + 1] = DiffTrack.REWIND_TARGET
            else:
                diff_count[i + 1][j + 1] = diff_count[i][j + 1]
                diff_track[i + 1][j + 1] = DiffTrack.REWIND_BASE

    base_cursor = base_len
    target_cursor = target_len

    while base_cursor > 0 or target_cursor > 0:
        if diff_track[base_cursor][target_cursor] == DiffTrack.MATCH:
            result.append((base_trace[base_cursor - 1], trace[target_cursor - 1]))
            base_cursor -= 1
            target_cursor -= 1
        elif diff_track[base_cursor][target_cursor] == DiffTrack.REWIND_BASE:
            result.append((base_trace[base_cursor - 1], None))
            base_cursor -= 1
        elif diff_track[base_cursor][target_cursor] == DiffTrack.REWIND_TARGET:
            result.append((None, trace[target_cursor - 1]))
            target_cursor -= 1
        else:
            raise Exception("Unreachable")

    result.reverse()
    return result
