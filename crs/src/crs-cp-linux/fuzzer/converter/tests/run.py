import logging
import sys
import traceback
from argparse import ArgumentParser, Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import reproduce_blob
from ..lib.KasanRunner import (
    get_kasan_report_global,
)
from ..trace import cleanup_tracer, init_tracer


def prepare_poc2pov(harness: Path):
    test_suites_dir = Path(__file__).with_name("test_suites")
    poc2pov_dir = test_suites_dir / "poc2pov"
    testlang_dir = test_suites_dir / "testlang"
    poc_dir = poc2pov_dir / "poc"

    harness_stem = harness.stem
    poc_stem = (
        harness_stem[:-2] if harness_stem.endswith("-2") else harness_stem
    )  # Take off -2
    poc = poc_dir / f"{poc_stem}"
    testlang = testlang_dir / f"{harness_stem}.txt"

    return poc, harness, testlang


def main(args: Namespace):
    logger = logging.getLogger(__name__)

    kasan_kernel: Path | None = args.kasan_kernel
    no_kasan_kernel: Path = args.no_kasan_kernel
    test_suites_dir = Path(__file__).with_name("test_suites")
    poc2pov_dir = test_suites_dir / "poc2pov"
    # pov2pov_dir = Path(__file__).with_name("pov2pov")

    test_work_dir = Path(__file__).with_name("test-workdir")
    test_work_dir.mkdir(exist_ok=True)

    test_tracer_dir = test_work_dir / "tracer"
    test_tracer_dir.mkdir(exist_ok=True)

    temp_dir = TemporaryDirectory()
    kasan_runner_dir = Path(temp_dir.name)

    # Test PoC2PoV
    try:
        target_harnesses = (poc2pov_dir / "harness").iterdir()

        init_tracer(no_kasan_kernel, test_tracer_dir)
        if kasan_kernel is not None:
            init_kasan_runner(kasan_kernel, kasan_runner_dir)
        for harness_src in target_harnesses:
            # if "CVE-2022-32250" != harness_src.name:
            #     continue
            try:
                poc, harness, testlang = prepare_poc2pov(harness_src)
                for out in reproduce_blob(poc, harness, testlang):
                    if kasan_kernel is not None:
                        kasan_report = get_kasan_report_global(harness, out)
                        poc_name = Path(poc).name
                        if not kasan_report.is_crash():
                            logger.warning(
                                f"Produced blob (for {poc_name}) does not trigger KASAN crash"
                            )
                            continue
                        else:
                            logger.info(
                                f"Produced blob (for {poc_name}) triggers KASAN crash succesfully"
                            )
                            logger.info("Restarting KASan runner for clean result...")
                            init_kasan_runner(kasan_kernel, kasan_runner_dir)

                    output_path = test_work_dir / f"{harness.name}.pov"
                    with open(output_path, "wb") as out_file:
                        out_file.write(out)
                    found = True
                    break

                if not found:
                    logger.warn("Harness %s not appropriate for PoC %s", harness, poc)
                logger.info(
                    "Reproduction trial done using PoC %s for harness %s", poc, harness
                )

            except Exception as e:
                logger.warning(
                    "Error occurred during blob reproduction. Ignoring this PoC..."
                )
                logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))

    finally:
        cleanup_tracer()
        temp_dir.cleanup()


if __name__ == "__main__":
    parser = ArgumentParser(
        "converter_test",
        description="Tests converter module",
    )
    parser.add_argument(
        "--kasan-kernel", type=Path, help="Directory of KASan enabled kernel"
    )
    parser.add_argument(
        "--no-kasan-kernel",
        type=Path,
        help="Directory of KASan disabled kernel",
        required=True,
    )
    args = parser.parse_args()

    log_file = Path("./converter_test.log")

    console_log_handler = logging.StreamHandler(sys.stderr)
    file_log_handler = logging.FileHandler(log_file)

    logging.basicConfig(
        format="%(asctime)s %(levelname)8s| %(name)32s| %(message)s",
        handlers=[console_log_handler, file_log_handler],
        level=logging.DEBUG,
    )

    main(args)
