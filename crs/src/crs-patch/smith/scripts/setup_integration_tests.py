#!/usr/bin/env python3
import argparse
import subprocess
import shutil
import os
from pathlib import Path
from typing import Optional, Callable, Tuple, List

# Type alias for the schema setup
SetupSchema = Tuple[Path, str, Optional[str], Optional[Callable]]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--cleanup', action='store_true')
    return p.parse_args()

def git_clone(args: argparse.Namespace, schema: SetupSchema) -> bool:
    dst, url, commit, _ = schema
    changed = False

    if args.cleanup:
        shutil.rmtree(dst)

    # Create the parent directory if it does not exist
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not dst.exists():
        subprocess.check_call(['git', 'clone', url, dst])
        changed = True

    if commit is not None:
        # TODO: Check if the commit has been changed
        subprocess.check_call(['git', 'checkout', commit], cwd=dst)

    return changed

def setup_all(args: argparse.Namespace, schemas: List[SetupSchema]):
    for schema in schemas:
        setup_single(args, schema)

def setup_single(args: argparse.Namespace, schema: SetupSchema):
    changed = git_clone(args, schema)
    if changed:
        apply_handler(schema)

def apply_handler(schema: SetupSchema):
    dst, _, _, handler = schema
    if handler:
        handler(dst)

def chdir_to_root():
    # Our script assumes that it is run from the root of the schemasitory
    os.chdir(Path(__file__).parent.parent)

def run_commands(cmds, cwd):
    for cmd in cmds:
        subprocess.check_call(cmd, shell=True, cwd=cwd)

# Each handler should be a function that takes a Path object as an argument
def setup_cp(dst: Path):
    run_commands([
        'make cpsrc-prepare',
        'make docker-build',
        'make docker-config-local',
        #         './run.sh -x build'
    ], dst)

def setup_cp_jenkins(dst: Path):
    shutil.copy(Path(__file__).parent / "patches" / "jenkins-cp.patch",
                dst / "jenkins-cp.patch")
    run_commands([
        'git apply jenkins-cp.patch'
    ], dst)
    setup_cp(dst)
    run_commands([
        './run.sh prebuild'
    ], dst)

def setup_cp_jenkins_orig(dst: Path):
    shutil.copy(Path(__file__).parent / "patches" / "jenkins-cp-orig.patch",
                dst / "jenkins-cp-orig.patch")
    run_commands([
        'git apply jenkins-cp-orig.patch'
    ], dst)
    setup_cp(dst)

def setup_cp_repo(dst: Path):
    for cp in dst.iterdir():
        setup_cp(cp)

def setup_arvo(dst: Path):
    cp_repo = dst / 'cp'
    setup_cp_repo(cp_repo)

def setup_syzbot(dst: Path):
    cp_repo = dst / 'syzbot_scrape' / 'aixcc-cp'
    setup_cp_repo(cp_repo)

def make_schemas() -> List[SetupSchema]:
    return [
        # (dst, url, commit (optional), handler)
        (Path('3rd/mock-cp'),
         'git@github.com:Team-Atlanta/mock-cp.git', None, setup_cp),
        (Path('3rd/challenge-001-linux-cp'),
         'git@github.com:Team-Atlanta/challenge-001-linux-cp.git', None, setup_cp),
        (Path('3rd/asc-challenge-002-jenkins-cp'),
         'git@github.com:Team-Atlanta/asc-challenge-002-jenkins-cp.git', None, setup_cp_jenkins),
        (Path('3rd/asc-challenge-002-jenkins-cp-orig'),
         'git@github.com:Team-Atlanta/asc-challenge-002-jenkins-cp-orig.git',
         None, setup_cp_jenkins_orig),
        (Path('3rd/challenge-004-nginx-cp'),
         'git@github.com:Team-Atlanta/challenge-004-nginx-cp.git', None, setup_cp),
        (Path('3rd/benchmark'),
         'git@github.com:Team-Atlanta/benchmark.git', None, None),
        (Path('3rd/cp-linux'),
         'git@github.com:Team-Atlanta/cp-linux.git', 'syzbot-to-aixcc-cp', setup_syzbot),
        (Path('3rd/arvo2exemplar'),
         'git@github.com:Team-Atlanta/arvo2exemplar.git', 'bic-check', setup_arvo),
        (Path('3rd/cp-user-babynote'),
         'git@github.com:Team-Atlanta/cp-user-babynote.git', None, setup_cp),
        (Path('3rd/cp-user-itoa'),
         'git@github.com:Team-Atlanta/cp-user-itoa.git', None, setup_cp),
        (Path('3rd/cp-user-libcue'),
         'git@github.com:Team-Atlanta/cp-user-libcue.git', None, setup_cp),
        # TODO: Add more schemas
    ]

def main():
    args = parse_args()

    chdir_to_root()
    setup_all(args, make_schemas())

if __name__ == '__main__':
    main()
