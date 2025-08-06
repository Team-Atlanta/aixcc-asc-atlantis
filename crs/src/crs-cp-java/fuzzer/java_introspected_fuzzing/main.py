import sys
import traceback
from fuzzercfg import FuzzerCfg
from introspected_fuzzing import IntrospectedFuzzing

from log import *

def load_general_fuzzing_cfg(cfg_file: str, log_file: str) -> FuzzerCfg:
    try:
        cfgs = {}
        with open(cfg_file, "r") as f:
            for line in f:
                parts = line.strip().split(" = ")
                if len(parts) != 2:
                    continue
                key, value = parts
                cfgs[key.strip()] = value.strip()

        general_cfg = FuzzerCfg(
            work_dir=cfgs['work_dir'],
            classpath=cfgs['classpath'],
            instrumentation_includes=cfgs['instrumentation_includes'],
            harness=cfgs['harness'],
            total_fuzzing_time=cfgs['total_fuzzing_time'],
            keep_going=cfgs['keep_going'],
            corpus_dir=cfgs['corpus_dir'],
            dict_file=cfgs['dict_file'],
            log_file=log_file,
            reset=False,
        )
    except Exception as e:
        error(f"Parsing cfg from {cfg_file} error: {e}")
        error(traceback.format_exc())
        sys.exit(1)

    return general_cfg

def do_introspected_fuzzing():
    """
    Main logic of introspected fuzzing.
    """
    # check arg number
    if len(sys.argv) != 4:
        error(f"Jazzer Introspected Fuzzer: Attach to one existing Jazzer instances for introspection & fuzzing.")
        error(f"Usage: {sys.argv[0]} <target_cfg> <target_log> <log_file>")
        sys.exit(1)

    setup_logger(sys.argv[3])
    general_cfg = load_general_fuzzing_cfg(sys.argv[1], sys.argv[2])
    info(f"Start introspected fuzzing with cfg: {general_cfg}")

    IntrospectedFuzzing(general_cfg).run()


def main():
    do_introspected_fuzzing()


if __name__ == "__main__":
    main()
