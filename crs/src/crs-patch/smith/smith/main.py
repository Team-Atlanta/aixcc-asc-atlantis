#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import traceback
from pathlib import Path
from typing import List, Tuple, Any

import coloredlogs
import pandas

from dotenv import load_dotenv
from .challenge import Challenge
from .env import Environment
from .fault_localizer import (
    BICFullFaultLocalizer,
    StackTraceFaultLocalizer,
    get_fault_localizer,
    get_available_fault_localizers,
)
from .generator import (
    AiderRevert,
    AiderWhole,
    SWEGenerator,
    get_prompt_generator,
    get_available_prompt_generators
)
from .model import get_model, GPT4o, get_available_models
from .patcher import Patcher
from .loader import load_challenge
from .bug import Bug
from .patch_trial import PatchOutcome, PatchTrial

ROOT = Path(__file__).parent.absolute()
logger = logging.getLogger(__name__)

def summarize_results(results: List[Tuple[PatchOutcome, PatchTrial]]):
    compile_success = 0
    functional_success = 0
    security_success = 0

    for (outcome, _) in results:
        if outcome.is_compile_error():
            continue
        compile_success += 1

        if outcome.is_functional_error():
            continue
        functional_success += 1

        if outcome.is_security_error():
            continue
        security_success += 1

    total = len(results)
    return [
        f"{compile_success} / {total}",
        f"{functional_success} / {total}",
        f"{security_success} / {total}"
    ]


def write_bug_results_to_csv(bug: Bug, results: List[Tuple[PatchOutcome, PatchTrial]]):
    lists = [outcome.to_list() for (outcome, trial) in results]
    df = pandas.DataFrame(lists, columns = ['name', 'compile', 'functional', 'security', 'msg'])
    df = df.set_index(df.columns[0], drop=True)
    bug_dir = bug.get_output_dir()
    bug_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(bug_dir / "results.csv")


def write_summary_to_csv(args: argparse.Namespace, results: List[List[Any]]):
    df = pandas.DataFrame(results, columns = ['name', 'compile', 'functional', 'security'])
    df = df.set_index(df.columns[0], drop=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output_dir / "results.csv")
    print(df)

def _check_args(args):
    if args.prompt_generator == SWEGenerator and \
        args.fault_localizer != BICFullFaultLocalizer:
        raise ValueError("SWEGenerator only works with BICFullFaultLocalizer")
    if args.prompt_generator == AiderWhole and \
        args.fault_localizer != StackTraceFaultLocalizer:
        raise ValueError("SWEGenerator only works with StackTraceFaultLocalizer")
    if args.prompt_generator == AiderRevert  and \
        args.fault_localizer != BICFullFaultLocalizer:
        raise ValueError("AiderRevert only works with BICFullFaultLocalizer")


def _parse_args():
    now = datetime.datetime.now()

    # TODO: Think about other arguments for patching
    parser = argparse.ArgumentParser(description='Our AIxCC patch system')
    parser.add_argument('-r', '--request-file', help='Patch request', type=Path, required=True)
    parser.add_argument('-t', '--challenge-dirs',
                        nargs='+', type=Path, help='challenge directory in benchmark',
                        required=True)
    parser.add_argument('-o', '--output-dir', type=Path, help='Output directory',
                        default=os.path.join(ROOT, f"output-{now.strftime('%Y%m%d%H%M%S')}"))
    parser.add_argument('-e', '--engine', type=str, nargs='+', help='OpenAI engine(s)',
                        default=[GPT4o.name()], choices=get_available_models())
    parser.add_argument('-n', '--num_samples', type=int,
                        help='Number of samples to generate', default=1)
    parser.add_argument('-f', '--fault-localizer', choices=get_available_fault_localizers(),
                        help='A fault localizer', default=BICFullFaultLocalizer.name(), nargs='?')
    parser.add_argument('--fl-top-k', type=int, help='Top k locatiions to consider', default=5)
    parser.add_argument('--fl-use-k', type=int, help='Use k-th fault.', default=-1)
    parser.add_argument('-p', '--prompt_generator', type=str,
                        help='A prompt generator to use', default=AiderWhole.name(),
                        choices=get_available_prompt_generators())
    parser.add_argument('--validate', action='store_true', help='Validate the challenge')
    parser.add_argument('--num_evolves', type=int, help='Number of samples to evolve', default=0)
    args = parser.parse_args()

    args.fault_localizer = get_fault_localizer(args.fault_localizer)
    args.prompt_generator = get_prompt_generator(args.prompt_generator)
    _check_args(args)
    return args

def _localize_fault(args, challenge: Challenge):
    bug = challenge.bug
    fault_localizer = args.fault_localizer(challenge, bug, args.fl_top_k, args.fl_use_k)
    fault_localizer.localize()

def _generate_patch(args, challenge: Challenge):
    bug = challenge.bug
    generators = [
        args.prompt_generator(
            challenge,
            bug,
            get_model(engine)(),
            args.num_samples // len(args.engine)
        )
        for engine in args.engine
    ]
    patcher = Patcher(challenge, bug, generators, args.num_evolves)
    results = patcher.run_all()
    write_bug_results_to_csv(bug, results)
    return results

def _run_step(challenge_name, step_name, step_function, *args):
    logger.info(f"Running {step_name} for {challenge_name}...")
    try:
        return step_function(*args)
    except Exception as e: # pylint: disable=broad-exception-caught
        logger.warning(f"Failed to run {step_name.lower()} for {challenge_name}: {e}")
        traceback.print_exc()

def _preprocess_challenge(args, challenge: Challenge):
    challenge.prepare()
    if args.validate:
        # TODO: Enable this after fixing the issue
        # challenge.validate()
        pass
    _localize_fault(args, challenge)

def _setup_logging():
    for logger_name in ["__main__"]:
        coloredlogs.install(logger=logging.getLogger(logger_name),
                            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
                            level=logging.DEBUG)

    # Silencing unneccessary logs
    logging.getLogger('httpx').disabled = True
    logging.getLogger('LiteLLM').disabled = True
    logging.getLogger('asyncio').disabled = True
    logging.getLogger('docker').disabled = True
    logging.getLogger('simple_parsing').disabled = True
    logging.getLogger('urllib3').disabled = True
    loggers = logging.Logger.manager.loggerDict
    for ln in loggers:
        mute_list = ["markdown_it", "httpcore", "openai", "git", "simple_parsing"]
        if any([mute in ln for mute in mute_list]):
            logging.getLogger(ln).disabled = True

def main():
    load_dotenv()

    args = _parse_args()
    logger.info("Arguments: %s", args)

    # Load the challenge
    logger.info("Output directory: %s", args.output_dir)

    total_results = []
    env = Environment(args.output_dir)
    for challenge_dir in args.challenge_dirs:
        challenge_name = challenge_dir.name

        challenge = _run_step(challenge_name, "Loading",
                              load_challenge, env, challenge_dir, args.request_file)
        _run_step(challenge_name, "Preprocessing", _preprocess_challenge, args, challenge)
        results = _run_step(challenge_name, "Patch generating",
                            _generate_patch, args, challenge)

        total_results.append([challenge.name] + summarize_results(results))

    write_summary_to_csv(args, total_results)


if __name__ == "__main__":
    _setup_logging()
    main()
