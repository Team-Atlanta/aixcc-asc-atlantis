#!/usr/bin/env python3
from pathlib import Path
from typing import List
import argparse
import asyncio
import logging
import os

import coloredlogs
import toml

from .checker.corpus_checker import CorpusChecker
from .runner import Runner, SmithRunner, LoopRunner
from .utils.challenge import ChallengeProject
from .utils.common import reset_dir, rsync_file, run_command
from .watcher import RequestWatcher

coloredlogs.install(fmt='%(asctime)s %(levelname)s [CRS-PATCH] %(message)s')

ROOT_DIR = Path(__file__).parent

EXTRA_ARGS = ["-n", "2", "--num_evolves", "1"]

RUNNER_CONFIG = {
    "s0-rvt-gpt": ["-p", "aider-revert", "-e", "oai-gpt-4o", "-n", "5", "--num_evolves", "1"],
    "s1-adr-gpt": ["-p", "aider", "-e", "oai-gpt-4o", *EXTRA_ARGS],
    "s2-swe-gpt": ["-p", "swe-agent", "-e", "oai-gpt-4o", *EXTRA_ARGS],
    "s3-loop": [],
    "s4-whl-gpt": ["-p", "aider-whole", "-e", "oai-gpt-4o", "-f", "stacktrace", *EXTRA_ARGS],
    "s5-adr-cld": ["-p", "aider", "-e", "claude-3.5-sonnet", "-f", "stacktrace_full", *EXTRA_ARGS],
    "s6-swe-cld": ["-p", "swe-agent", "-e", "claude-3.5-sonnet", *EXTRA_ARGS],
    # Try gemini pro if gpt and claude fails, might need larger context window
    "s7-adr-gmn": ["-p", "aider", "-e", "gemini-1.5-pro", *EXTRA_ARGS],
    "s8-swe-gmn": ["-p", "swe-agent", "-e", "gemini-1.5-pro", *EXTRA_ARGS],
}


class RequestIterator(object):
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self._queue.get()

        if item is None:
            raise StopAsyncIteration

        return item


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cp-root", type=Path, help="cp-root directory")
    parser.add_argument("--crs-scratch", type=Path, help="scratch space")
    parser.add_argument("--validate", action="store_true", \
                        help="Validate generated patches with corpuses")
    return parser.parse_args()


def prepare(cp_root: Path, patch_dir: Path) -> dict[str, Path]:
    cp_map = {}
    cp_paths = [cp for cp in cp_root.iterdir() if cp.is_dir()]

    for cp_path in cp_paths:
        try:
            copied_dir = patch_dir / cp_path.name
            reset_dir(copied_dir)

            original = ChallengeProject.load(cp_path)
            cp = original.clone(copied_dir)
            cp_map[cp.name()] = copied_dir
        except Exception as e:
            logging.error(f"Failed to prepare {cp_path.name}: {e}")

    return cp_map


def submit(request_file: Path, patch_diff: Path):
    logging.info(f"Submitting {patch_diff} for {request_file}")
    request = toml.load(request_file)
    verifier_dir = ROOT_DIR / "verifier"

    if "cpv_uuid" not in request:
        logging.error("cpv_uuid is not found in the request")
        return

    cmd = [
        "python3", "verifier.py",
        "submit_gp",
        "--cpv-uuid", request["cpv_uuid"],
        "--patch", f"'{patch_diff}'",
    ]
    run_command(" ".join(cmd), verifier_dir)


async def execute(
        queue: asyncio.Queue,
        runners: List[Runner],
        args: argparse.Namespace,
        cp_map: dict[str, Path]
    ):
    async for request in RequestIterator(queue):
        logging.info(f"Processing request: {request}")

        # TODO: refactor this, currently it's selecting new corpus testset for each request.
        checker = CorpusChecker(args, request, cp_map)
        try:
            patch = None
            # Synchrnous execution
            for runner in runners:
                patches = await runner.run(request)
                if args.validate:
                    patches = filter(checker.check_patch, patches)
                patch = next(patches, None)
                if patch is not None:
                   # Early exit if a valid patch is found
                   break

            if patch is None:
                logging.info(f"No patch found for {request}")
                continue

            logging.info(f"Found a valid patch for {request}")
            submit(request, patch)
        except Exception as e:
            logging.error(f"Failed to process request: {request}: {e}")


def setup_async(
        requests_dir: Path,
        runners: List[Runner],
        args: argparse.Namespace,
        cp_map: dict[str, Path]
    ):
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()  # version 3.10: Removed the loop parameter.

    futures = [
        RequestWatcher(loop, queue, requests_dir).watch(),
        execute(queue, runners, args, cp_map)
    ]

    loop.run_until_complete(asyncio.gather(*futures))


if __name__ == '__main__':
    args = parse_args()

    logging.info(f'cp-root: {args.cp_root}')
    logging.info(f'crs-scratch: {args.crs_scratch}')

    requests_dir = args.crs_scratch / "requests"
    patch_dir = args.crs_scratch / "patch"
    corpus_dir = args.crs_scratch / "corpus"

    user_dir = Path(os.path.expanduser("~"))
    smith_output_dir = user_dir / "smith-output"
    loop_output_dir = user_dir / "loop-output"
    reset_dir(smith_output_dir)
    reset_dir(loop_output_dir)

    cp_map = prepare(args.cp_root, patch_dir)

    runners = [
        *(
            SmithRunner(cp_map, smith_output_dir, ROOT_DIR / "smith", name, args)
            if "loop" not in name else LoopRunner(cp_map, loop_output_dir, ROOT_DIR / "loop")
            for name, args in RUNNER_CONFIG.items()
        ),
    ]

    setup_async(requests_dir, runners, args, cp_map)
