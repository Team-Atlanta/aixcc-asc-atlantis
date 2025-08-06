import hashlib
import os
import pickle
import shutil
import signal
import time
import traceback
import uuid
from filelock import FileLock
from logging import getLogger
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path
from tempfile import TemporaryDirectory

from ..lib import SkyTracer, SSyscall, STrace

TIMEOUT = 120


class Tracer:
    def __init__(self, kernel: Path, work_dir: Path):
        self.kernel = kernel
        self.work_dir = work_dir
        self.start_tracer_subprocess()

    def __del__(self):
        self.trx.send(None)

        if not self.trx.poll(TIMEOUT) and self.subprocess.pid is not None:
            os.kill(self.subprocess.pid, signal.SIGINT)
            time.sleep(1)
            if not self.trx.poll(TIMEOUT):
                self.subprocess.kill()

        self.subprocess.join()

    def start_tracer_subprocess(self):
        logger = getLogger(__name__)
        main_side, sub_side = Pipe(duplex=True)
        self.trx = main_side
        process_name = uuid.uuid4().hex[:8]
        self.subprocess = Process(name=f"TRACE-{process_name}", target=self.process, args=(sub_side,))
        self.subprocess.start()
        if not self.trx.poll(TIMEOUT):
            logger.error("Tracer subprocess failed to bootup!")
            raise Exception("Tracer subprocess failed to bootup!")

        self.trx.recv()

    def trace_one_with_timeout(self, source_bin: Path, blob: bytes = b"", timeout=TIMEOUT) -> STrace | None:
        result = None

        self.trx.send((source_bin, blob))

        if not self.trx.poll(timeout) and self.subprocess.pid is not None:
            os.kill(self.subprocess.pid, signal.SIGINT)
            time.sleep(1)
            if not self.trx.poll(timeout):
                self.subprocess.kill()
            self.subprocess.join()
            self.start_tracer_subprocess()
        elif self.trx.poll():
            result = self.trx.recv()

        return result

    def process(self, trx: Connection):
        logger = getLogger(__name__)
        try:
            with TemporaryDirectory(dir=self.work_dir) as temp_dir:
                start_t = time.perf_counter()
                with SkyTracer(self.kernel, temp_dir) as tracer:
                    logger.info("Tracer initialization done in %.3lfs.", time.perf_counter() - start_t)
                    trx.send(None)
                    while (job_request := trx.recv()) is not None:
                        start_t = time.perf_counter()
                        source_bin, blob = job_request
                        logger.info("Starting trace of %s...", source_bin)

                        # Dumb workaround to locate PoC binary within tracer.workdir
                        target_bin = tracer.workdir / source_bin.name
                        if source_bin != target_bin:
                            shutil.copy(source_bin, target_bin)
                        trace_result = tracer.trace_target(target_bin, blob)
                        logger.info("Trace done in %.3lfs.", time.perf_counter() - start_t)

                        if trace_result is None:
                            logger.error("Error occurred while performing trace.")

                        trx.send(trace_result)

        except Exception as e:
            logger.error("Error in tracer subprocess!")
            logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))
        finally:
            trx.send(None)


tracer: Tracer | None = None
cache: Path | None = None


def init_tracer(kernel: Path, work_dir: Path, cache_dir: Path):
    global tracer
    global cache
    logger = getLogger(__name__)

    if tracer is None:
        logger.info("Starting global tracer session...")
        tracer = Tracer(kernel.absolute(), work_dir.absolute())
        cache = cache_dir
    else:
        logger.warn("Tracer initialization requested while trace session is up. Ignoring...")


def cleanup_tracer():
    global tracer
    logger = getLogger(__name__)

    if tracer is not None:
        start_t = time.perf_counter()
        logger.info("Cleaning up global tracer session...")
        tracer = None
        logger.info("Tracer cleanup done in %.3lfs.", time.perf_counter() - start_t)
    else:
        logger.warn("Tracer cleanup requested while trace session is down. Ignoring...")


def restart_tracer(kernel: Path, work_dir: Path, cache_dir: Path):
    logger = getLogger(__name__)
    logger.info("Restarting tracer for clean result...")
    cleanup_tracer()
    init_tracer(kernel, work_dir, cache_dir)


def get_save_names(cache_dir: Path, hash_digest: str):
    trace_pickle_path = cache_dir / f"{hash_digest}.trace"
    bin_copy = cache_dir / f"{hash_digest}.bin"
    return trace_pickle_path, bin_copy


def get_file_hash(blob: bytes) -> str:
    logger = getLogger(__name__)
    hasher = hashlib.sha256()
    hasher.update(blob)
    digest = hasher.hexdigest()
    logger.debug("Blob hashed into: %s", digest)
    return digest


def save_trace(blob: bytes, cache_dir: Path, trace: list[SSyscall]):
    logger = getLogger(__name__)

    digest = get_file_hash(blob)
    logger.info("Saving trace cache of id %s into file...", digest)
    trace_pickle_path, bin_copy = get_save_names(cache_dir, digest)
    with open(bin_copy, "wb") as blob_out:
        blob_out.write(blob)
    logger.info("Blob backup saved into: %s", bin_copy)

    with open(trace_pickle_path, "wb") as trace_out:
        pickle.dump(trace, trace_out, pickle.HIGHEST_PROTOCOL)
    logger.info("Trace saved into: %s", trace_pickle_path)


def load_trace_if_exists(blob: bytes, cache_dir: Path) -> list[SSyscall] | None:
    logger = getLogger(__name__)

    digest = get_file_hash(blob)
    trace_pickle_path, bin_copy = get_save_names(cache_dir, digest)

    if not trace_pickle_path.is_file() or not bin_copy.is_file():
        logger.info("Prepared trace of id %s doesn't exist", digest)
        return None

    with open(bin_copy, "rb") as blob_in:
        src_blob = blob_in.read()

    if src_blob != blob:
        logger.info("Prepared trace of id %s doesn't exist", digest)
        return None

    logger.info("Loading trace of id %s from file...", digest)
    trace: list[SSyscall] | None = None
    with open(trace_pickle_path, "rb") as trace_in:
        trace = pickle.load(trace_in)

    return trace


def get_lock(blob: bytes, cache_dir: Path):
    hash_digest = get_file_hash(blob)
    lock_path = cache_dir / f"{hash_digest}.lock"
    return FileLock(lock_path)


def generate_trace_harness(harness_bin: Path, blob: bytes, use_cache: bool = True) -> list[SSyscall] | None:
    global tracer
    global cache
    logger = getLogger(__name__)

    if tracer is None or cache is None:
        logger.error("Trace requested before tracer is ready. Aborting...")
        raise Exception("Trace requested before tracer is ready. Aborting...")

    with get_lock(blob, cache):
        if use_cache:
            trace_cache = load_trace_if_exists(blob, cache)
            if trace_cache is not None:
                logger.debug("Using cache for trace request of target harness: %s", str(harness_bin))
                return trace_cache

        start_t = time.perf_counter()
        logger.debug("Starting trace of target harness: %s", str(harness_bin))
        trace = tracer.trace_one_with_timeout(harness_bin, blob)

        if trace is not None:
            for syscall in trace.syscalls:
                logger.debug("%s", syscall)

        if trace:
            logger.debug("Trace done in %.3lfs.", time.perf_counter() - start_t)
            save_trace(blob, cache, trace.syscalls)
            return trace.syscalls

        logger.debug("Trace failed in %.3lfs.", time.perf_counter() - start_t)

        restart_tracer(tracer.kernel, tracer.work_dir, cache)

        logger.info("Retrying on fresh session...")

        start_t = time.perf_counter()
        logger.debug("Starting trace of target harness: %s", str(harness_bin))
        trace = tracer.trace_one_with_timeout(harness_bin, blob)

        if trace is not None:
            for syscall in trace.syscalls:
                logger.debug("%s", syscall)

        if trace:
            logger.debug("Trace done in %.3lfs.", time.perf_counter() - start_t)
            save_trace(blob, cache, trace.syscalls)
            return trace.syscalls

        logger.debug("Trace failed in %.3lfs.", time.perf_counter() - start_t)
        return None
