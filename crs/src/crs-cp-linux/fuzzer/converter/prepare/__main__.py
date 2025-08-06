import logging
import sys
import traceback
from argparse import ArgumentParser, Namespace
from multiprocessing import freeze_support
from pathlib import Path
from tempfile import TemporaryDirectory

from . import save_trace
from .worker import TracePool, trace_one_with_timeout


def main(args: Namespace):
    logger = logging.getLogger(__name__)

    logger.info("Starting preparation for converter...")

    bin_dir: Path = args.bin_dir
    out_dir: Path = args.out_dir
    kernel: Path = args.kernel
    work_dir: Path | None = args.work_dir
    cpus: int = args.cpus

    temp_dir: TemporaryDirectory | None = None

    logger.debug("Arguments:")
    logger.debug("    Input binary directory => %s", bin_dir)
    logger.debug("    Output directory => %s", out_dir)
    logger.debug("    Kernel directory => %s", kernel)
    logger.debug("    Work directory => %s", work_dir)
    logger.debug("    nCPUs => %d", cpus)

    if work_dir is None:
        logger.debug("Derived Arguments:")
        temp_dir = TemporaryDirectory()
        work_dir = Path(temp_dir.name)
        logger.debug("    Work directory => %s", work_dir)

    try:
        bins = list(bin_dir.iterdir())
        if len(bins) == 0:
            logger.info("Binary list: Empty")
        else:
            logger.info("Binary list:")
            for binary in bins:
                logger.info("    - %s", binary.name)

        if not isinstance(cpus, int) or cpus < 1:
            logger.warning("The number of available CPUs is invalid. Fallback to value 1...")
            cpus = 1

        if cpus == 1:
            for source_bin in bins:
                try:
                    result = trace_one_with_timeout(source_bin, kernel, work_dir)
                    if result is None:
                        logger.warning("Tracing took longer than timeout. ignoring this binary...")
                        continue

                    _, trace = result
                    save_trace(source_bin, out_dir, trace)
                except Exception as e:
                    logger.error("Error occurred during trace and save. Ignoring this binary...")
                    logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))

        else:
            pool = TracePool(cpus - 1, kernel, work_dir)
            result_it = pool.run(bins)

            while True:
                try:
                    result = next(result_it)
                    if result is None:
                        logger.warning("Tracing took longer than timeout. ignoring this binary...")
                        continue

                    source_bin, trace = result
                    save_trace(source_bin, out_dir, trace)
                except StopIteration:
                    break
                except Exception as e:
                    logger.error("Error occurred during trace and save. Ignoring this binary...")
                    logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))

    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    logger.info("Preparation Done.")


if __name__ == "__main__":
    freeze_support()
    parser = ArgumentParser(
        "converter.prepare",
        description="Prepares system call trace in advance",
    )
    parser.add_argument(
        "--bin-dir", type=Path, help="Directory of binaries to prepare traces", required=True
    )
    parser.add_argument("--out-dir", type=Path, help="Output directory", required=True)
    parser.add_argument(
        "--kernel",
        type=Path,
        help="Directory of tracer kernel",
        required=True,
    )
    parser.add_argument("--work-dir", type=Path, help="Work directory for tracing")
    parser.add_argument("--cpus", type=int, default=1, help="Max CPU count for parallel tracing")
    args = parser.parse_args()

    log_file = Path("./converter.prepare.log")

    if args.work_dir is not None:
        log_file = args.work_dir / "converter.prepare.log"

    console_log_handler = logging.StreamHandler(sys.stderr)
    console_log_handler.setLevel(logging.INFO)
    file_log_handler = logging.FileHandler(log_file)

    logging.basicConfig(
        format="%(asctime)s %(levelname)8s| %(processName)16s: %(name)32s| %(message)s",
        handlers=[console_log_handler, file_log_handler],
        level=logging.DEBUG,
    )

    logging.getLogger("pwnlib").setLevel(logging.ERROR)

    main(args)
