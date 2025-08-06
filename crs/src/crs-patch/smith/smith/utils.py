import subprocess
import logging
from typing import Tuple
from pathlib import Path

import difflib

logger = logging.getLogger(__name__)


def generate_diff(original_text: str, modified_text: str) -> str:
    # Split the input strings into lines
    original_lines = original_text.splitlines()
    modified_lines = modified_text.splitlines()

    # Create a Differ object
    differ = difflib.Differ()

    # Get the differences between the two sets of lines
    diff_result = differ.compare(original_lines, modified_lines)

    # Join the differences into a string
    diff_string = '\n'.join(diff_result)

    return diff_string

# TODO: move this to utils.py
#       currently unable due to a circular import (bug -> challenge -> utils -> bug)
def run_command(command: str, cwd: Path, timeout=None) -> Tuple[bytes, bytes, int]:
    try:
        proc = subprocess.Popen(command, cwd=cwd,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        logger.info(f"Run command: {cwd}$ {command}")
        stdout, stderr = proc.communicate(timeout=timeout)
        returncode = proc.returncode
        logger.info(f"Return code: {returncode}")
        return stdout, stderr, returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        logger.error(f"Timeout: {command}")
        return b'', b'Timeout', 1


def rsync_dir(src: Path, dst: Path) -> bool:
    command = f"rsync -a --delete {src}/. {dst}"
    stdout, stderr, returncode = run_command(command, Path("/"))
    if returncode == 0:
        return True
    else:
        logger.error(f"Failed to rsync {src} to {dst}")
        logger.error(f"stdout: {stdout!r}")
        logger.error(f"stderr: {stderr!r}")
        return False

def rsync_file(src: Path, dst: Path) -> bool:
    command = f"rsync -a --delete {src} {dst}"
    stdout, stderr, returncode = run_command(command, Path("/"))
    if returncode == 0:
        return True
    else:
        logger.error(f"Failed to rsync {src} to {dst}")
        logger.error(f"stdout: {stdout!r}")
        logger.error(f"stderr: {stderr!r}")
        return False
