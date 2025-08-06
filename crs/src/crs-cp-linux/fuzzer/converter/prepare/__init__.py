import filecmp
import hashlib
import logging
import pickle
import shutil
from pathlib import Path

from ..lib import SSyscall
from .worker import trace_one_with_timeout


def get_save_names(prep_dir: Path, hash_digest: str):
    trace_pickle_path = prep_dir / f"{hash_digest}.trace"
    source_bin_copy = prep_dir / f"{hash_digest}.bin"
    return trace_pickle_path, source_bin_copy


def get_file_hash(source: Path) -> str:
    logger = logging.getLogger(__name__)
    hasher = hashlib.sha256()
    buf = bytearray(128 * 1024)
    memv = memoryview(buf)

    with open(source, "rb", buffering=0) as src_file:
        while n := src_file.readinto(memv):
            hasher.update(memv[:n])

    digest = hasher.hexdigest()
    logger.debug("File hashed into: %s", digest)
    return digest


def save_trace(source_bin: Path, prep_dir: Path, trace: list[SSyscall]):
    logger = logging.getLogger(__name__)

    logger.info("Saving trace of %s into file...", source_bin)
    digest = get_file_hash(source_bin)
    trace_pickle_path, source_bin_copy = get_save_names(prep_dir, digest)

    shutil.copyfile(source_bin, source_bin_copy)
    logger.info("Source binary backup copied into: %s", source_bin_copy)
    with open(trace_pickle_path, "wb") as trace_out:
        pickle.dump(trace, trace_out, pickle.HIGHEST_PROTOCOL)
    logger.info("Trace saved into: %s", trace_pickle_path)


def load_trace_if_exists(source_bin: Path, prep_dir: Path) -> list[SSyscall] | None:
    logger = logging.getLogger(__name__)

    digest = get_file_hash(source_bin)
    trace_pickle_path, source_bin_copy = get_save_names(prep_dir, digest)

    if (
        not trace_pickle_path.is_file()
        or not source_bin_copy.is_file()
        or not filecmp.cmp(source_bin, source_bin_copy, shallow=False)
    ):
        logger.info("Prepared trace of %s doesn't exist", source_bin)
        return None

    logger.info("Loading trace of %s from file...", source_bin)
    trace: list[SSyscall] | None = None
    with open(trace_pickle_path, "rb") as trace_in:
        trace = pickle.load(trace_in)

    return trace


def get_trace(source_bin: Path, prep_dir: Path | None, kernel: Path, work_dir: Path) -> list[SSyscall]:
    if prep_dir is not None:
        saved_trace = load_trace_if_exists(source_bin, prep_dir)
        if saved_trace is not None:
            return saved_trace
    trace = trace_one_with_timeout(source_bin, kernel, work_dir)
    if trace is None:
        raise Exception(f"Error occurred while performing trace of {source_bin}.")
    return trace[1]
