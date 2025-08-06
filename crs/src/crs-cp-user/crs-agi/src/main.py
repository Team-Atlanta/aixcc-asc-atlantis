import os
import argparse
import time
import sys
import re
import shlex
import litellm

from pathlib import Path
from collections import namedtuple

import rich
from loguru import logger

from llm.models import LLM
from llm.plugins import (ExecutePython, ExecuteShell, Workspace,
    get_workspace_plugins, get_mentalcare_plugins, )
from llm.replayer import Replayer, Recorder
from llm.crs import CRSWorkspace, get_crs_plugins
from llm.prompt import Prompt, load_prompt
from llm.errors import PluginSuccess, PluginErrorGivingUp, PluginErrorRetry
from llm.runner import LLMRunner
from llm.util import md5sum

ROOT = Path(os.path.dirname(__file__))


def cp_root(cp):
    return (ROOT / "../cp_root" / cp).resolve()


def get_llm(opts, plugins=None):
    recorder = Recorder(opts.record) if opts.record else None
    replayer = Replayer(opts.replay, seed=opts.seed) if opts.replay else None

    return LLM.setup(opts.model,
                     plugins=plugins,
                     temperature=opts.temperature,
                     replayer=replayer,
                     recorder=recorder)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cp", type=Path, help="a path to the challenge project", required=True)
    parser.add_argument("--delete", action="store_true", help="delete the workspace on exit", default=False)
    parser.add_argument("--workspace", type=Path, help="(re-)use the specified workspace", default=None)
    parser.add_argument("--temperature", type=float, help="Temperature for LLM", default=None)
    parser.add_argument("--replay", type=Path, help="Replay the session", default=None)
    parser.add_argument("--record", type=Path, help="Record the session", default=None)
    parser.add_argument("--seed", help="Random seed for llm", nargs='?', const=1, type=int)
    parser.add_argument("--no-rebuild", action="store_true", help="Don't reset/build the CP from scratch", default=False)
    parser.add_argument("--model", help="Specify the llm model (e.g., gpt-4o, gemini-1.5-pro)", default="gpt-4o")
    parser.add_argument("--debug", action="store_true", help="Print out VERY VERBOSE messages (litellm)", default=False)

    args = parser.parse_args()

    if not args.cp.exists():
        args.cp = cp_root(args.cp)
    else:
        args.cp = args.cp.resolve()

    assert args.cp.exists()

    if args.debug:
        litellm.set_verbose=True

    return args


class PoVOracleCache:
    def __init__(self):
        self.cache = {}
        self.results = {}

    def is_cached(self, pn):
        pn = Path(pn).resolve()
        if not pn.exists():
            return (False, None)

        # common path; avoiding md5sum
        if pn in self.cache:
            (cached_mtime, cached_md5) = self.cache[pn]
            if cached_mtime >= pn.lstat().st_mtime:
                return (True, cached_md5)

        md5 = md5sum(open(pn).read())
        if not pn in self.cache:
            return (True, md5)
        else:
            (_, cached_md5) = self.cache[pn]
            if cached_md5 == md5:
                return (True, cached_md5)
            else:
                return (False, md5)

    def put(self, pn, md5, result):
        pn = str(pn.resolve())
        self.results[pn] = result
        self.cache[pn] = (pn.lstat().st_mtime, md5)

    def get(self, pn):
        pn = str(pn.resolve())
        return self.results.get(pn, None)


class PoVOracle:
    name = "pov"

    def __init__(self):
        self.candidates = []
        self.povs = []
        self.sanitizers = []
        self.cache = PoVOracleCache()

    def get_all_pov_results(self):
        return self.povs

    def check(self, runner):
        workspace = runner.workspace

        self.sanitizers = workspace.get_sanitizers()

        # extract all run_pov() from the tool calls
        pairs = []
        for tc in runner.prompt.get_all_toolcalls():
            # TODO. from execute_python and more relaxed matches?
            if tc.function == "execute_shell" \
               and "code" in tc.arguments \
               and "run.sh run_pov" in tc.arguments["code"]:
                cmdargs = shlex.split(tc.arguments["code"].strip())
                if len(cmdargs) == 4:
                    pairs.append((cmdargs[2], cmdargs[3]))
                else:
                    logger.warning(f"Incorrect cmdline arguments: {cmdargs}")

        # TODO. add other potential pairs (e.g., every files under tmp/?)
        self.candidates = list(set(pairs))

        # verify
        out = []
        for blob, harness in self.candidates:
            (cached, md5) = self.cache.is_cached(blob)
            if not cached:
                pov = workspace.run_pov(blob, harness)
                self.cache.put(blob, md5, pov)
            else:
                pov = self.cache.get(blob)
            out.append(pov)

        self.povs = out

        return out


if __name__ == "__main__":
    args = parse_args()

    workspace = CRSWorkspace(cp=args.cp,
                             rebuild=not args.no_rebuild,
                             root=args.workspace,
                             delete=args.delete)

    # TODO. clang parsers for C/C++, codeql?
    packages = ["numpy", "pwntools", "r2pipe", "capstone", "angr", "standard libs"]
    plugins = [
        ExecutePython(workspace, packages=packages),
        ExecuteShell(workspace),
        get_workspace_plugins(workspace),
        get_crs_plugins(workspace),
        get_mentalcare_plugins(workspace)
    ]

    prompt = Prompt()
    prompt.append(load_prompt("aixcc-crs.txt"), role="system")
    prompt.append(load_prompt("aixcc-background.txt"))
    prompt.append(load_prompt("aixcc-context.txt",
                              cp=Path(args.cp).name,
                              sanitizers=workspace.get_sanitizers()))

    prompt.append("Your goal is to generate a <blob_file> that triggers the sanitizer enumerated in `project.yaml`. "
                  "Put the generated <blob_file> under `tools.tmpdir()`! "
                  "To check if the generated blob file and harness properly working, you can verify it with "
                  "`run.sh run_pov <blob_file> <harness_name>`. "
                  ""
                  "1) You might first want to check a project description file at `project.yaml`, "
                  "and the testing script, `run.sh`; "
                  "2) Examine how the testing (`run.sh run_tests`) internally works; "
                  "3) Plan the BEST strategies -- stick to it!; "
                  "and lastly, 4) find the crashing <blob_file> and harness!"
                  "Once you find it properly work with `run.sh run_pov <blob_file> <harness_name>`, "
                  "put it under `tools.tmpdir()` and finish the session.")

    # prompt.append("Your goal is to recognize blob files for testing "
    #               "and the name of testing harness."
    #               "To check if the found blob file and harness working, you can verify it with "
    #               "`run.sh run_pov <blob_file> <harness_name>`."
    #               "You might want to check a project description file at `project.yaml`, "
    #               "and the testing script, `run.sh`. "
    #               "The testing can be run with `run.sh run_tests`.\n\n"
    #               "Your job is to list up <blob_file> and <harness_name> that properly work with `run.sh run_pov`!")


    # prompt.append("Your task is to find a bug-triggering input in the given CP. "
    #               "Store the found input under 'work/' or `tools.tmpdir()` in your python code. "
    #               "You can start analyzing the test harnesses and understand how the program works first. "
    #               "`./run.sh` is a good starting point."
    #               "You should first understand how `run.sh run_tests` works "
    #               "and how the test input relates to the bug in the target program.")

    llm = get_llm(args, plugins=plugins)
    runner = LLMRunner(args, llm, prompt, workspace,
                       oracles=[PoVOracle()])

    sanitizers = set(workspace.get_sanitizers())
    all_povs = []

    (state, oracles) = runner.run()

    povs = oracles.get("pov", None)
    if povs:
        for pov in povs:
            all_povs.append(pov)
            logger.info(f"Found PoV @{pov.blob} with @{pov.harness} by {pov.caught_by()}")

    # got all sanitizers?
    remaining = sanitizers - set([pov.caught_by() for pov in all_povs])
    if len(remaining) == 0:
        logger.info(f"Found all sanitizers!")
