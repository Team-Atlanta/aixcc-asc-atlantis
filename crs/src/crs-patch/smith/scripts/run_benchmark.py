#!/usr/bin/env python

"""
Run benchmark for the given CPV or CP.

Usage:
    ; List all CPVs
    $ ./scripts/run_benchmark.py list [--cp <path> ...]

    ; Run benchmark for a CP
    $ ./scripts/run_benchmark.py run --cp <path> [-s/--strategy <strategy>] [-d/--dry-run]

    ; Run benchmark for a CPV
    $ ./scripts/run_benchmark.py run --cpv <path> [-s/--strategy <strategy>] [-d/--dry-run]

Note:
    - Use CPV blob path for CPV
    - Strategy can be selected from the following:
        [s0, s1, s3, s4, s5, s6, s7]
    - Use `-d` option to do a dry run
"""

from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import argparse
import datetime
import subprocess
import sys
import dotenv

REQUESTS_DIR    = Path('./requests').resolve()

class FaultLocalization(Enum):
    STACKTRACE_FULL = 'stacktrace_full'
    BIC_FULL        = 'bic_full'
    LLMLOCAL        = 'llmlocal'
    ANY             = 'bic_full'


class PromptGenerator(Enum):
    AIDER       = 'aider'       # File-level fault localization
    SWE_AGENT   = 'swe-agent'   # No fault localization is needed
    AIDERWHOLE  = 'aider-whole' # File-level fault localization
    AIDERREVERT  = 'aider-revert' # File-level fault localization


class Model(Enum):
    GPT_3_5_TURBO       = 'oai-gpt-3.5-turbo'
    GPT_4_TURBO         = 'oai-gpt-4-turbo'
    GPT_4O              = 'oai-gpt-4o'
    GEMINI_1_5_PRO      = 'gemini-1.5-pro'
    CLAUDE_3_HAIKU      = 'claude-3-haiku'
    CLAUDE_3_SONNET     = 'claude-3-sonnet'
    CLAUDE_3_OPUS       = 'claude-3-opus'
    CLAUDE_3_5_SONNET   = 'claude-3.5-sonnet'


@dataclass
class Strategy:
    fault_localization: FaultLocalization
    prompt_generator: PromptGenerator
    model: Model
    num_evolves: int = 0
    # Project specific?
    # Language specific?

    def __str__(self):
        return (
            f"{self.fault_localization.value}:"
            f"{self.prompt_generator.value}:"
            f"{self.model.value}:"
            f"{self.num_evolves}"
        )

strategy_names = {
    's0': Strategy(FaultLocalization.BIC_FULL, PromptGenerator.AIDER, Model.GPT_4O, 1),
    's1': Strategy(FaultLocalization.ANY, PromptGenerator.SWE_AGENT, Model.GPT_4O, 1),
    's2': None, # LOOP
    's3': Strategy(FaultLocalization.STACKTRACE_FULL, PromptGenerator.AIDERWHOLE, Model.GPT_4O, 1),
    's4': Strategy(FaultLocalization.STACKTRACE_FULL, PromptGenerator.AIDER,
                   Model.CLAUDE_3_5_SONNET, 1),
    's5': Strategy(FaultLocalization.ANY, PromptGenerator.SWE_AGENT, Model.CLAUDE_3_5_SONNET, 1),
    's6': Strategy(FaultLocalization.BIC_FULL, PromptGenerator.AIDER, Model.GEMINI_1_5_PRO, 1),
    's7': Strategy(FaultLocalization.ANY, PromptGenerator.SWE_AGENT, Model.GEMINI_1_5_PRO, 1),
}

def print_strategies():
    for name, strategy in strategy_names.items():
        if strategy is None:
            continue
        print(f"{name}: {strategy}")

def print_result(output_dir: Path):
    results_csv = output_dir / 'results.csv'
    if not results_csv.exists():
        print("No results found")
        return

    print(results_csv.read_text())

def get_trackers():
    # pylint: disable=all

    # Submodule can't be used
    cps_patch_path = Path('./3rd/CRS-patch')
    if not cps_patch_path.exists():
        subprocess.run(['git', 'clone', 'git@github.com:Team-Atlanta/CRS-patch', '3rd/CRS-patch'],
                        check=True)
    sys.path.append(str(cps_patch_path))

    from tracker import TimeTracker, CostTracker # type: ignore
    return TimeTracker(), CostTracker()

def run_smith(target_dir: Path,
              request_file: Path,
              output_dir: Path,
              strategy: Strategy,
              dry_run=False):
    name = request_file.stem
    print(f"Running {name} with strategy {strategy}")
    cmd = [
        'python3', '-m', 'smith.main',
        '-t', str(target_dir),
        '-r', str(request_file),
        '-n', '5',
        '-f', strategy.fault_localization.value,
        '--fl-top-k', '5',
        '-p', strategy.prompt_generator.value,
        # TODO: Option for prompting
        '--num_evolves', str(strategy.num_evolves),
        '-e', strategy.model.value,
        '-o', str(output_dir / name),
        '--validate',
    ]
    print(' $ ' + ' '.join(cmd))

    time_tracker, cost_tracker = get_trackers()

    # IMPORTANT: Start cost tracker before time tracker
    # cost_tracker.start()
    time_tracker.start()

    if not dry_run:
        log_file = output_dir / 'log' / f'{name}.txt'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if log_file.exists():
            log_file.unlink()
        log_file.write_text(' [+] Strategy: ' + str(strategy) + '\n')
        log_file.write_text(' [+] Smith command: ' + ' '.join(cmd) + '\n')

        try:
            subprocess.run(cmd, stdout=open(log_file, 'w'), stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError:
            print(open(log_file).read())
            return

    # IMPORTANT: End time tracker before cost tracker
    time_tracker.end()
    # cost_tracker.end()

    print(" [+] Elapsed time: ", time_tracker.get_value())
    # print(" [+] Cost: ", cost_tracker.get_value())
    print_result(output_dir / name)

class CP(ABC):
    @abstractmethod
    def get_target_cp(self, blob: Path) -> Path:
        pass

    @abstractmethod
    def get_request_file(self, blob: Path) -> Path:
        pass

class CP_LINUX(CP):
    dir = Path('./3rd/challenge-001-linux-cp').resolve()

    def get_target_cp(self, blob: Path) -> Path:
        return self.dir

    def get_request_file(self, blob: Path) -> Path:
        harness_name = blob.name.split('_solve')[0]
        return REQUESTS_DIR / f'cp-linux-{harness_name}.toml'

class CP_JENKINS(CP):
    dir = Path('./3rd/asc-challenge-002-jenkins-cp').resolve()

    def get_target_cp(self, blob: Path) -> Path:
        return self.dir

    def get_request_file(self, blob: Path) -> Path:
        harness_name = blob.stem
        if harness_name == 'sample_solve':
            harness_name = 'id_1'
        harness_name = harness_name.replace('_', '-')
        return REQUESTS_DIR / f'cp-jenkins-harness-{harness_name}.toml'

class MOCK_CP(CP):
    dir = Path('./3rd/mock-cp').resolve()

    def get_target_cp(self, blob: Path) -> Path:
        return self.dir

    def get_request_file(self, blob: Path) -> Path:
        if 'cpv_1' in blob.parts:
            return REQUESTS_DIR / 'mock-cp-cpv-1.toml'
        elif 'cpv_2' in blob.parts:
            return REQUESTS_DIR / 'mock-cp-cpv-2.toml'
        else:
            raise ValueError(f"Unknown mock blob: {blob}")

class CP_NGINX(CP):
    dir = Path('./3rd/challenge-004-nginx-cp').resolve()

    def get_target_cp(self, blob: Path) -> Path:
        return self.dir

    def get_request_file(self, blob: Path) -> Path:
        return REQUESTS_DIR / 'cp-nginx-sample.toml'

class CP_ARVO(CP):
    dir = Path('./3rd/arvo2exemplar/cp').resolve()

    def _get_arvo_id(self, blob: Path):
        for part in blob.parts:
            if part.startswith('arvo-'):
                return part.split('-')[1]
        else:
            return None

    def get_target_cp(self, blob: Path) -> Path:
        arvo_id = self._get_arvo_id(blob)
        return self.dir / f'arvo-{arvo_id}'

    def get_request_file(self, blob: Path) -> Path:
        arvo_id = self._get_arvo_id(blob)
        return REQUESTS_DIR / 'arvo' / f'{arvo_id}.toml'

class CP_SYZBOT(CP):
    dir = Path('./3rd/cp-linux/syzbot_scrape/aixcc-cp').resolve()

    def _get_syzbot_id(self, blob: Path):
        for part in blob.parts:
            if part.startswith('cp-'):
                if part == 'cp-linux':
                    continue
                return part.split('-')[1]
        else:
            raise ValueError(f"Unknown syzbot blob: {blob}")

    def get_target_cp(self, blob: Path) -> Path:
        syzbot_id = self._get_syzbot_id(blob)
        return self.dir / f'cp-{syzbot_id}'

    def get_request_file(self, blob: Path) -> Path:
        syzbot_id = self._get_syzbot_id(blob)
        return REQUESTS_DIR / 'syzbot' / f'{syzbot_id}.toml'

def get_available_cps():
    return [
        CP_LINUX(),
        CP_JENKINS(),
        MOCK_CP(),
        CP_NGINX(),
        CP_ARVO(),
        CP_SYZBOT(),
    ]

def get_target_cp_and_request_file(blob: Path):
    blob = blob.resolve()
    for cp in get_available_cps():
        if cp.get_target_cp(blob) in blob.parents:
            return cp.get_target_cp(blob), cp.get_request_file(blob)
    else:
        raise ValueError(f"Unknown blob: {blob}")

def get_all_cp_dir():
    cps = []
    for cp in get_available_cps():
        cps.append(cp.dir)
    return cps

def list_cpv(cp_all):
    blobs = []
    for cp in cp_all:
        for blob in cp.rglob('blobs/*'):
            blobs.append(blob)
    return blobs

def main():
    dotenv.load_dotenv()
    print_strategies()

    ap = argparse.ArgumentParser()
    subparsers = ap.add_subparsers(dest='action')
    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('--cp', nargs='+', type=Path)
    run_parser = subparsers.add_parser('run')
    run_parser.add_argument('-d', '--dry-run', action='store_true')
    run_parser.add_argument('--cp', nargs='+', type=Path)
    run_parser.add_argument('--cpv', type=Path)
    run_parser.add_argument('-s', '--strategy', type=str, choices=strategy_names.keys())
    args = ap.parse_args()

    if args.action is None:
        ap.print_help()
        return
    elif args.action == 'list':
        blobs = list_cpv(args.cp or get_all_cp_dir())
        for blob in blobs:
            print(blob)
    elif args.action == 'run':
        target_cpv = [args.cpv] if args.cpv else list_cpv(args.cp or get_all_cp_dir())
        current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = Path(f'output-{current_time}')
        print("Output directory:", output_dir)
        for blob in target_cpv:
            target_cp, request_file = get_target_cp_and_request_file(blob)
            run_smith(target_cp,
                      request_file,
                      output_dir,
                      strategy_names[args.strategy],
                      args.dry_run)

if __name__ == '__main__':
    main()
