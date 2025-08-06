import logging
import shutil
import subprocess

from pathlib import Path


def run_command(cmd: str, cwd=None, env=None, timeout=None, pipe_stderr=False) -> bytes:
    try:
        logging.info(f"{cwd if cwd is not None else ''}$ {cmd}")
        return subprocess.check_output(
            cmd,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.STDOUT if pipe_stderr else None,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            env=env
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"{cmd} exited with code {e.returncode}")
        logging.error(e.output)
        return b""


def reset_dir(dir_path: Path):
    shutil.rmtree(dir_path, ignore_errors=True)
    dir_path.mkdir(parents=True, exist_ok=True)

def rsync_file(src: Path, dst: Path):
    run_command(f"rsync -a {src} {dst}")
