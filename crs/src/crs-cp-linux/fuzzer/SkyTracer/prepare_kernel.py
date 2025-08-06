#!/usr/bin/env python3

import sys
import argparse
import subprocess
import logging
import coloredlogs
from pathlib import Path

coloredlogs.install(fmt='%(asctime)s %(levelname)s %(message)s')

def error(msg):
    print(msg)
    sys.exit(-1)

def copy_src(src, out):
    logging.info("Copy src..")
    subprocess.check_output(["cp", "-r", str(src), str(out)])

def update_conf(conf):
    logging.info("Update .config..")
    ret = ""
    with open(str(conf), "rt") as f:
        for line in f.readlines():
            line = line.strip()
            if not line.startswith("#") and "HAVE" not in line and "HAS" not in line:
                if "KCOV" in line: line = "#" + line
                if "KASAN" in line: line = "#" + line
            ret += line + "\n"

    with open(str(conf), "wt") as f:
        f.write(ret)

HEADER = """
void skytracer_copy_to_user(void __user *to, const void *from, unsigned long n);
void skytracer_copy_from_user(const void *to, const void __user *from, unsigned long n);
"""

CODE = """
void skytracer_copy_to_user(void __user *to, const void *from, unsigned long n)
{
  return;
}
EXPORT_SYMBOL(skytracer_copy_to_user);

void skytracer_copy_from_user(const void *to, const void __user *from, unsigned long n)
{
  return;
}
EXPORT_SYMBOL(skytracer_copy_from_user);
"""

INST_MAP = {
  "instrument_copy_to_user": "skytracer_copy_to_user(to, from, n);",
  "instrument_copy_from_user_before": "skytracer_copy_from_user(to, from, n);"
}

def update_src(out):
    logging.info("Update src..")
    ret = HEADER
    with open(out / "include/linux/instrumented.h", "rt") as f:
        inst = None
        for line in f.readlines():
            ret += line
            if line.startswith(" *"): continue
            for key in INST_MAP:
                if key in line:
                    inst = INST_MAP[key]
                    break
            if inst and "{" in line:
                ret += inst+"\n"
                inst = None

    with open(out / "include/linux/instrumented.h", "wt") as f:
        f.write(ret)
    with open(out / "lib/usercopy.c", "at") as f:
        f.write(CODE)

def build_symtabs(vmlinux):
    if not vmlinux.exists():
        error(f"{vmlinux} does not exist, meaning that we fail to compile the kernel")
    logging.info("Build symtabs..")
    path = str(vmlinux) + ".symtabs"
    f = open(path, "wt")
    for item in subprocess.check_output(["objdump", "-t", vmlinux]).decode("utf-8").split("\n")[1:-1]:
        item = item.strip()
        if ".text" not in item: continue
        tmp = item.split(" ")
        addr = tmp[0]
        name = tmp[-1]
        f.write("%s, %s\n"%(name, addr))
    f.close()

def instrument(target):
    update_conf(target / ".config")
    update_src(target)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, help="target instrument dir")
    parser.add_argument("--symtabs", type=Path, help="target symtab vmlinux")
    args = parser.parse_args()
    if args.instrument: instrument(args.instrument)
    if args.symtabs: build_symtabs(args.symtabs)
