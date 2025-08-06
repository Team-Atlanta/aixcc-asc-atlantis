import time
from logging import getLogger
from pathlib import Path

from .kasan_runner import KasanReport, KasanRunner


def get_kasan_report_global(
    work_dir: Path, kasan_kernel: Path, harness_bin: Path, blob: bytes
) -> KasanReport:
    logger = getLogger(__name__)

    blob_path = work_dir / "test_blob.bin"
    with open(blob_path, "wb") as f:
        f.write(blob)

    kasan_runner = KasanRunner(kasan_kernel, work_dir)

    start_t = time.perf_counter()
    logger.debug("Preparing KASan report of target: %s", str(harness_bin))

    report = kasan_runner.exec_target(harness_bin, blob_path)
    logger.debug("KASan report ready in %.3lfs.", time.perf_counter() - start_t)
    return report
