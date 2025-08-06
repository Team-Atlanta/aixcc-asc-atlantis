#!/usr/bin/env python3

import asyncio
import os
import sys
import glob
import argparse
from pathlib import Path
import time
from crs_utils.logfactory import LOG, logging_init
from crs_utils.runner import Runner
from crs_utils.cp import CP
from crs_utils.config import Config
from crs_utils.settings import DEV

def is_java_project():
    # example if it's a java project
    print("Not implemented yet. Always return False.")
    return False

def load_projects(cp_root, lang = "")-> list[CP]:
    projects = []
    for fname in glob.glob(f"{cp_root}/**/project.yaml"):
        cp = CP(Path(fname).parent)
        if cp.lang == lang or is_java_project():
            projects.append(cp)
    if len(projects) == 0:
        LOG.error(f"Cannot find any projects with lang:{lang} in {cp_root}")
        # HyungSeok asked to exit with 0 in this case
        sys.exit(0)
    return projects 

def init(cp_root):
    return load_projects(cp_root, "java")

# It must be executed once CRS begins
def prepare(cp):
    runner = Runner(cp, Config().workdir, Config().builddir)
    runner.prepare()

def build_cp(cp):
    runner = Runner(cp, Config().workdir, Config().builddir)
    runner.build_cp()


def run(cp):
    runner = Runner(cp, Config().workdir, Config().builddir)
    # runner.cp.build(False)
    if runner.cp.is_built() == False:
        runner.build_cp()
    runner.run()

def main(cp_root, cmd):
    java_cps = init(cp_root)

    java_cps_names = [cp.name for cp in java_cps]
    LOG.info(f"java_cps: {java_cps_names}")

    for cp in java_cps:
        if cmd == "prepare":
            prepare(cp)
        elif cmd == "build_cp":
            build_cp(cp)
        elif cmd == "run":
            try:
                run(cp)
            except:
                sys.exit(-1)
        else:
            print("Invalid command; must be one of [prepare | reset | run]")




if __name__ == "__main__":
    Config().load("/crs-java.config")

    os.environ["TOTAL_FUZZING_TIME"] = str(Config().total_fuzzing_time)

    parser = argparse.ArgumentParser()
    parser.add_argument("--cp-root", help="cp-root directory")
    parser.add_argument("--cmd", help="command [prepare | build_cp | run]")
    args = parser.parse_args()

    logging_init(Config().builddir)

    LOG.info("Start running the CRS")

    main(Path(args.cp_root), args.cmd)
