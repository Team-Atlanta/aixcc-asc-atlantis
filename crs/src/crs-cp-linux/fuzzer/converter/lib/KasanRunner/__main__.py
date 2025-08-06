import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from .kasan_runner import KasanReport, KasanRunner


def get_kasan_report(kernel: Path, harness: Path, blob: Path, work_dir: Path | None = None) -> KasanReport:
    kernel = Path(kernel)
    harness = Path(harness)
    temp_dir: TemporaryDirectory | None = None

    if work_dir is None:
        temp_dir = TemporaryDirectory()
        work_dir = Path(temp_dir.name)

    try:
        # Do NOT reuse crash detection session for now
        kasan_runner = KasanRunner(kernel, work_dir)
        report = kasan_runner.exec_target(harness, blob)
        return report
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run target with crash detection")
    parser.add_argument("--kernel", required=True, help="Path to the kernel directory")
    parser.add_argument("--harness", required=True, help="Path to the instrumented harness binary")
    parser.add_argument("--blob", required=True, help="Blob to be passed to the target")
    parser.add_argument("--work-dir", default=None, help="Working directory to store temporary files")
    args = parser.parse_args()

    print(get_kasan_report(args.kernel, args.harness, args.blob, args.work_dir))
