import os
import importlib.util
import sys
import subprocess

from pathlib import Path

import rich

ROOT = Path(os.path.dirname(__file__))


# borrowed from: https://stackoverflow.com/a/1051266/656011
def check_for_package(package):
    """`check_for_package(package_name) -> bool`. \
It returns `True` if a package exists. Otherwise, `False`."""

    if package in sys.modules:
        return True
    elif (spec := importlib.util.find_spec(package)) is not None:
        try:
            module = importlib.util.module_from_spec(spec)

            sys.modules[package] = module
            spec.loader.exec_module(module)

            return True
        except ImportError:
            return False
    else:
        return False


def echo(output):
    """`echo(output) -> None`. \
It prettyprints the output variable."""

    rich.print(output)

def tmpdir():
    """`tmpdir() -> Path`. It returns a temporary directory."""

    return (ROOT / ".." / "tmp").resolve()

def cpdir():
    """`cpdir() -> Path`. It returns a directory of the challenge project (CP)."""

    return (ROOT / ".." / "cp").resolve()

def run_tests():
    """`run_tests() -> bool`. \
It runs the functionality tests to see if the challenge project (CP) runs properly."""

    try:
        result = subprocess.run(["./run.sh", "run_tests"], cwd=cpdir(), check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def run_pov(blob_file, harness_name):
    """`run_pov(blob_file, harness_name) -> bool`. \
It runs the binary data blob against specified harness."""

    try:
        result = subprocess.run(["./run.sh", "run_pov", blob_file, harness_name],
                                cwd=cpdir(), check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def run_build():
    """`run_build() -> bool`. \
It runs the binary data blob against specified harness."""

    try:
        result = subprocess.run(["./run.sh", "build"],
                                cwd=cpdir(), check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def get_dict(name):
    """`get_dict(<name>) -> content`. \
It returns a sample dictionary for libfuzzer."""

    if not name.endswith(".dict"):
        name = name + ".dict"

    pn = Path(ROOT / "dictionaries" / name)
    if pn.exists():
        return open(pn).read()
    else:
        return "N/A"
