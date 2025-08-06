import functools
import logging
import sys
import traceback
from argparse import ArgumentParser, Namespace
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from . import reproduce_blob
from .lib import (
    SSyscall,
    get_kasan_report_global,
)
from .mimic import get_blob_score
from .prepare import get_trace
from .project import DEFAULT_SANITIZERS, get_sanitizer_list
from .trace import cleanup_tracer, init_tracer


def write_blob(path: Path, blob: bytes):
    logger = logging.getLogger(__name__)
    if len(blob) > 2_097_152:
        # TODO: Save this blob as minimization candidate and process it
        logger.error("Blob size is limited to 2MiB by the rules. Ignoring this output")
        raise Exception("Blob size is limited to 2MiB by the rules. Ignoring this output")

    with open(path, "wb") as out_file:
        out_file.write(blob)

    logger.info("Output blob written to: %s", path)


def run_one(
    job: tuple[Path, list[SSyscall]],
    work_dir: Path,
    cache_dir: Path,
    harness: Path,
    testlang: Path,
    no_kasan_kernel: Path,
    kasan_kernel: Path | None,
    out_seed_dir: Path,
    out_dir: Path,
    sanitizers: list[str],
):
    logger = logging.getLogger(__name__)
    with TemporaryDirectory(dir=work_dir) as tmp_dir:
        work_dir = Path(tmp_dir)
        init_tracer(no_kasan_kernel, work_dir, cache_dir)

        seed_serial = 0
        poc, poc_trace = job
        try:
            found = False
            coverage = 0

            kasan_runner_dir = work_dir / "kasan_runner"
            kasan_runner_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Crash detector work directory: %s", kasan_runner_dir)

            for out in reproduce_blob(poc_trace, harness, testlang):
                write_blob(out_seed_dir / f"{poc.name}-{seed_serial}.bin", out)
                seed_serial += 1

                if kasan_kernel is not None:
                    kasan_report = get_kasan_report_global(kasan_runner_dir, kasan_kernel, harness, out)
                    if not kasan_report.is_crash(sanitizers):
                        if not kasan_report.timed_out:
                            kasan_report = get_kasan_report_global(
                                kasan_runner_dir, kasan_kernel, harness, out
                            )

                        if not kasan_report.is_crash(sanitizers):
                            logger.info(
                                f"Produced blob (for {poc.name}) does not trigger KASAN crash. Searching other candidates..."
                            )
                            continue

                    logger.info(
                        f"Produced blob (for {poc.name}) triggers KASAN crash succesfully. Choosing this candidate..."
                    )
                    write_blob(out_dir / f"{poc.name}.pov", out)
                    found = True
                    break
                else:
                    blob_score = get_blob_score(poc_trace, harness, out)
                    if blob_score <= coverage:
                        continue
                    coverage = blob_score
                    write_blob(out_dir / f"{poc.name}.pov", out)
                    found = True

            if not found:
                logger.warning(
                    "Harness %s is considered not appropriate for PoC %s. Skipping...",
                    harness,
                    poc,
                )

            logger.info("Reproduction trial done using PoC %s for harness %s.", poc, harness)

        except Exception as e:
            logger.warning("Error occurred during blob reproduction. Ignoring this PoC...")
            logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))

        finally:
            cleanup_tracer()


def main(args: Namespace):
    logger = logging.getLogger(__name__)

    logger.info("Starting Converter...")

    poc_dir: Path = args.poc_dir
    harness: Path = args.harness
    testlang: Path = args.testlang
    prep_dir: Path | None = args.prep_dir
    proj_def: Path | None = args.proj_def
    work_dir: Path | None = args.work_dir
    kasan_kernel: Path | None = args.kasan_kernel
    no_kasan_kernel: Path = args.no_kasan_kernel
    out_dir: Path = args.out_dir
    out_seed_dir: Path | None = args.out_seed_dir
    cpus: int = args.cpus

    temp_dir: TemporaryDirectory | None = None

    logger.debug("Arguments:")
    logger.debug("    PoC directory => %s", poc_dir)
    logger.debug("    Harness file => %s", harness)
    logger.debug("    TestLang file => %s", testlang)
    logger.debug("    Preparation directory => %s", prep_dir)
    logger.debug("    Project definition file => %s", proj_def)
    logger.debug("    Work directory => %s", work_dir)
    logger.debug("    KASan enabled kernel directory => %s", kasan_kernel)
    logger.debug("    KASan disabled kernel directory => %s", no_kasan_kernel)
    logger.debug("    PoV output directory => %s", out_dir)
    logger.debug("    Seed output directory => %s", out_seed_dir)
    logger.debug("    nCPUs => %d", cpus)

    logger.debug("Derived Arguments:")
    if work_dir is None:
        temp_dir = TemporaryDirectory()
        work_dir = Path(temp_dir.name)
        logger.debug("    Work directory => %s", work_dir)

    if out_seed_dir is None:
        out_seed_dir = work_dir / "seeds"
        out_seed_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("    Seed output directory => %s", out_seed_dir)

    cache_dir = work_dir / "trace_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("    Trace cache directory => %s", cache_dir)

    pocs = list(poc_dir.iterdir())
    poc_traces: list[tuple[Path, list[SSyscall]]] = list()

    if len(pocs) == 0:
        logger.info("PoC list: Empty")
    else:
        logger.info("PoC list:")
        for poc in pocs:
            logger.info("    - %s", poc.name)

    logger.info("Loading PoC Traces...")
    for poc in pocs:
        try:
            trace = get_trace(poc, prep_dir, no_kasan_kernel, work_dir)
            poc_traces.append((poc, trace))
            logger.info("Trace for %s done.", poc)
        except Exception as e:
            logger.warning(
                "Error occurred while processing trace of PoC %s. Ignoring this PoC...",
                poc,
            )
            logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))

    logger.info("Loading Sanitizer list...")
    sanitizers = DEFAULT_SANITIZERS
    if proj_def is not None:
        sanitizers = get_sanitizer_list(proj_def)

    if len(sanitizers) == 0:
        logger.info("Sanitizer list: Empty")
    else:
        logger.info("Sanitizer list:")
        for sanitizer in sanitizers:
            logger.info("    - %s", sanitizer)

    if not isinstance(cpus, int) or cpus < 1:
        logger.warning("The number of available CPUs is invalid. Fallback to value 1...")
        cpus = 1

    run_one_worker = functools.partial(
        run_one,
        work_dir=work_dir,
        cache_dir=cache_dir,
        harness=harness,
        testlang=testlang,
        no_kasan_kernel=no_kasan_kernel,
        kasan_kernel=kasan_kernel,
        out_seed_dir=out_seed_dir,
        out_dir=out_dir,
        sanitizers=sanitizers,
    )

    with ProcessPoolExecutor(max_workers=cpus) as p:
        results = p.map(run_one_worker, poc_traces)
        for _ in range(len(poc_traces)):
            try:
                _ = next(results)
            except ValueError:
                pass
            except StopIteration:
                break

    if temp_dir is not None:
        temp_dir.cleanup()

    logger.info("Conversion step complete.")


if __name__ == "__main__":
    parser = ArgumentParser(
        "converter",
        description="Converts PoC system calls into harness compatible blobs",
    )
    parser.add_argument(
        "--poc-dir",
        type=Path,
        help="Directory of candidate PoC binaries",
        required=True,
    )
    parser.add_argument("--harness", type=Path, help="Path of harness binary", required=True)
    parser.add_argument("--testlang", type=Path, help="Path of harness reverse result", required=True)
    parser.add_argument("--prep-dir", type=Path, help="Directory of prepared traces")
    parser.add_argument("--proj-def", type=Path, help="Project definition file")
    parser.add_argument("--work-dir", type=Path, help="Work directory for conversion process")
    parser.add_argument("--kasan-kernel", type=Path, help="Directory of KASan enabled kernel")
    parser.add_argument(
        "--no-kasan-kernel",
        type=Path,
        help="Directory of KASan disabled kernel",
        required=True,
    )
    parser.add_argument("--out-dir", type=Path, help="Output directory for generated PoV", required=True)
    parser.add_argument("--out-seed-dir", type=Path, help="Output directory for all generated blobs")
    parser.add_argument("--cpus", type=int, default=1, help="Max number of concurrent conversion sessions")
    args = parser.parse_args()

    log_file = Path("./converter.log")

    if args.work_dir is not None:
        log_file = args.work_dir / "converter.log"

    console_log_handler = logging.StreamHandler(sys.stderr)
    console_log_handler.setLevel(logging.INFO)
    file_log_handler = logging.FileHandler(log_file)

    logging.basicConfig(
        format="%(asctime)s %(levelname)8s| %(processName)16s: %(name)32s| %(message)s",
        handlers=[console_log_handler, file_log_handler],
        level=logging.DEBUG,
    )

    logging.getLogger("pwnlib").setLevel(logging.ERROR)
    logging.getLogger("filelock").setLevel(logging.ERROR)

    main(args)
