import subprocess
from pathlib import Path
from typing import Sequence

from rusty_results.prelude import Err, Ok, Result

from loop.commons.fp.functions import procedure
from loop.commons.interaction.exceptions import CommandInteractionError

Command = tuple[str, Path]


def run_commands(commands: Sequence[Command]):
    return procedure(commands, run_command)


def run_command(
    command: Command, timeout: int | None = None
) -> Result[tuple[str, str], Exception]:

    line, cwd = command

    process = subprocess.Popen(
        line,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )

    stdout, stderr = process.communicate(timeout=timeout)

    return_code = process.returncode

    match return_code:
        case 0:
            return Ok((stdout.decode(), stderr.decode()))
        case _:
            return Err(
                CommandInteractionError(
                    stdout=stdout, stderr=stderr, return_code=return_code
                )
            )
