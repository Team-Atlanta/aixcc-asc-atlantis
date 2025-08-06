import logging
import multiprocessing
import os
import subprocess

from .logfactory import LOG, get_level

def run_cmd(cmd, cwd = None, env=None, LOG=LOG):
    new_env = os.environ.copy()
    if env:
        new_env.update(env)
    # Show the output only if logging level is DEBUG
    ret = subprocess.run(cmd, cwd = cwd, env = new_env, capture_output=True)
    if get_level(LOG) == logging.DEBUG:
        if ret.returncode != 0:
            LOG.error(f"Error running command: {cmd}")
            LOG.error(f"- stdout: {ret.stdout.decode('utf-8')}")
            LOG.error(f"- stderr: {ret.stderr.decode('utf-8')}")
    return ret

def empty_function():
    pass

run_sh_lock = multiprocessing.Lock()