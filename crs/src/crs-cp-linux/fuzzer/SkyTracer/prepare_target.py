#!/usr/bin/env python3

import sys
import glob
import argparse
from pathlib import Path

TRACER_INSTRUMENT = """
static void skytracer_init(int argc, char **argv, char **envp) {
  asm("mov $0xf000, %rax; syscall");
}

static void skytracer_fini(void) {
  asm("mov $0xf001, %rax; syscall");
}

__attribute__((section(".init_array"), used)) static typeof(skytracer_init) *init_p = skytracer_init;
__attribute__((section(".fini_array"), used)) static typeof(skytracer_fini) *fini_p = skytracer_fini;
"""

def instrument_src(target):
    with open(target, "rt") as f: code = f.read()
    if "main" not in code:
        print (f"{target} does not have main function")
        return False
    with open(target, "rt") as f:
        if f.read().endswith(TRACER_INSTRUMENT): return True
    with open(target, "wt") as f: f.write(code + TRACER_INSTRUMENT)
    return True

def instrument_dir(dir):
    for t in glob.glob(f"{dir}/*.c"):
        instrument_src(t)

def instrument_poc(poc_dir):
    for poc in glob.glob(f"{poc_dir}/CVE-*"):
        poc = Path(poc)
        target = poc / (poc.name + ".c")
        if target.exists():
            if not instrument_src(str(target)): sys.exit(-1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--poc-dir", help="target POC dir")
    parser.add_argument("--src", help="target src")
    parser.add_argument("--dir", help="target dir")

    args = parser.parse_args()
    if args.poc_dir: instrument_poc(args.poc_dir)
    elif args.src: instrument_src(args.src)
    elif args.dir: instrument_dir(args.dir)
