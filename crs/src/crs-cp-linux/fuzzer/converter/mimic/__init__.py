from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from pwnlib.util.cyclic import cyclic_gen

from ..lib import SSyscall
from ..template import Command, RecordLocation
from ..trace import generate_trace_harness
from ..trace.diff import diff_is_similar_weak, diff_trace


@dataclass
class CommandState:
    command: Command
    cyclic: cyclic_gen
    base_syscalls: list[SSyscall]
    full_copy_fields: set[Path]
    field_target_size: dict[Path, int]
    byte_mapping_targets: set[RecordLocation]
    mem_access_trial: int


def get_blob_score(trace_poc: list[SSyscall], harness: Path, blob: bytes) -> int:
    logger = getLogger(__name__)

    trace_harness = generate_trace_harness(harness, blob)
    if trace_harness is None:
        logger.warning("Trace failed while composing harness trace.")
        return 0

    diff_result = diff_trace(trace_poc, trace_harness, diff_is_similar_weak)
    return len(diff_result.common)
