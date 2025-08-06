import os
import queue
import shutil
import signal
import time
import traceback
import uuid
from logging import getLogger
from multiprocessing import JoinableQueue, Pipe, Process, Queue
from multiprocessing.connection import Connection
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

from ..lib import SkyTracer, SSyscall

TIMEOUT = 120


def trace_one(
    source_bin: Path, kernel: Path, work_dir: Path, blob: bytes = b""
) -> tuple[Path, list[SSyscall]]:
    logger = getLogger(__name__)

    with TemporaryDirectory(dir=work_dir) as temp_dir:
        logger.info("Starting trace of %s...", source_bin)
        start_t = time.perf_counter()
        trace_result = None
        with SkyTracer(kernel, temp_dir) as tracer:
            start_t_2 = time.perf_counter()
            logger.info("Tracer initialization done in %.3lfs.", start_t_2 - start_t)
            # Dumb workaround to locate PoC binary within tracer.workdir
            target_bin = tracer.workdir / source_bin.name
            if source_bin != target_bin:
                shutil.copy(source_bin, target_bin)
            logger.debug("Starting trace of target: %s", str(target_bin))
            trace_result = tracer.trace_target(target_bin, blob)
            logger.info("Trace done in %.3lfs.", time.perf_counter() - start_t_2)

        if trace_result is None:
            logger.error("Error occurred while performing trace.")
            raise Exception("Error occurred while performing trace.")

        return source_bin, trace_result.syscalls


def process_one(sender: Connection, job: Path, kernel: Path, work_dir: Path, blob: bytes = b""):
    logger = getLogger(__name__)

    result = None
    try:
        result = trace_one(job, kernel, work_dir, blob)
    except Exception as e:
        logger.error("Error processing trace for %d", job)
        logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))
    finally:
        sender.send(result)


def trace_one_with_timeout(
    source_bin: Path, kernel: Path, work_dir: Path, blob: bytes = b"", timeout=TIMEOUT
) -> tuple[Path, list[SSyscall]] | None:
    result = None
    res_recv, res_send = Pipe(duplex=False)
    process_name = uuid.uuid4().hex[:8]
    p = Process(
        name=f"TRACE-{process_name}",
        target=process_one,
        args=(res_send, source_bin, kernel, work_dir, blob),
    )
    p.start()

    if not res_recv.poll(timeout) and p.pid is not None:
        os.kill(p.pid, signal.SIGINT)
        time.sleep(1)
        if not res_recv.poll(timeout):
            p.kill()

    if res_recv.poll():
        result = res_recv.recv()

    p.join()
    return result


class TracePool:
    def __init__(self, cpus, kernel, work_dir):
        self.job_queue = JoinableQueue()
        self.result_queue = Queue()
        self.kernel = kernel
        self.work_dir = work_dir

        self.cpus = cpus
        self.processes = [
            Process(
                name=f"WORKER-{uuid.uuid4().hex[:8]}",
                target=self.mp_run,
                args=(self.job_queue, self.result_queue),
            )
            for _ in range(cpus)
        ]

    def mp_run(self, job_queue: JoinableQueue, result_queue: Queue):
        while True:
            try:
                job = job_queue.get(False)
            except queue.Empty:
                break

            result = None
            try:
                result = trace_one_with_timeout(job, self.kernel, self.work_dir, timeout=self.timeout)
            finally:
                result_queue.put(result)
                job_queue.task_done()

    def run(
        self, items: list, timeout=TIMEOUT
    ) -> Generator[tuple[Path, list[SSyscall]] | None, None, None]:
        self.timeout = timeout

        for item in items:
            self.job_queue.put(item)

        for proc in self.processes:
            proc.start()

        for _ in range(len(items)):
            yield self.result_queue.get()

        for proc in self.processes:
            proc.join()

        self.job_queue.close()
        self.result_queue.close()
