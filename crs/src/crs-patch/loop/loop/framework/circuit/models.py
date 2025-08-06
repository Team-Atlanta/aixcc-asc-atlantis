import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import click

from loop.commons.logging.hooks import use_logger
from loop.framework.action.variants import (
    DiffAction,
    RuntimeErrorAction,
    WrongFormatAction,
)
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection
from loop.framework.effect.variants import (
    CompilableEffect,
    DumbEffect,
    EmptyEffect,
    SoundEffect,
    UnknownErrorEffect,
    VulnerableEffect,
    WrongFormatEffect,
    WrongPatchEffect,
)
from loop.framework.wire.context import WireContext
from loop.framework.wire.models import Wire


@dataclass
class Circuit:
    id: str
    wires: list[Callable[[], Wire]]

    def run(
        self,
        detection: Detection,
        challenge_source: ChallengeSource,
        output_directory: Path,
    ):
        assert (
            output_directory.exists() and output_directory.is_dir()
        ), f"{output_directory} does not exist or is not a directory"

        # TODO: Parallelize this
        for wire_factory in self.wires:
            wire = wire_factory()

            logger = use_logger()

            logger.addHandler(
                logging.FileHandler(
                    output_directory
                    / f"{self.id}-{detection.cp_name}-{challenge_source.harness_name}-{wire.id}.log",
                    mode="w",
                )
            )

            wire_context: WireContext = {
                "history": [],
                "log_prefix": f"{self.id}-{detection.cp_name}-{challenge_source.harness_name}-{wire.id}",
                "logger": use_logger(),
            }

            is_sound_patch_found = False

            for index, (action, effect) in enumerate(
                wire.run(detection, challenge_source)(wire_context)
            ):
                match effect:
                    case DumbEffect():
                        filename = f"{wire_context['log_prefix']}-{index:05d}-dumb"
                    case CompilableEffect():
                        filename = (
                            f"{wire_context['log_prefix']}-{index:05d}-compilable"
                        )
                    case VulnerableEffect():
                        filename = (
                            f"{wire_context['log_prefix']}-{index:05d}-vulnerable"
                        )
                    case SoundEffect():
                        filename = f"{wire_context['log_prefix']}-{index:05d}-sound"
                    case WrongFormatEffect():
                        filename = (
                            f"{wire_context['log_prefix']}-{index:05d}-wrong-format"
                        )
                    case EmptyEffect():
                        filename = f"{wire_context['log_prefix']}-{index:05d}-empty"
                    case UnknownErrorEffect():
                        filename = (
                            f"{wire_context['log_prefix']}-{index:05d}-unknown-error"
                        )
                    case WrongPatchEffect():
                        filename = (
                            f"{wire_context['log_prefix']}-{index:05d}-wrong-patch"
                        )

                match action:
                    case DiffAction():
                        (output_directory / f"{filename}.diff").write_text(
                            action.content
                        )
                    case WrongFormatAction():
                        (
                            output_directory / f"{filename}.wrong-format.error"
                        ).write_text(str(action.error))
                    case RuntimeErrorAction():
                        (output_directory / f"{filename}.runtime.error").write_text(
                            str(action.error)
                        )

                match effect, action:
                    case SoundEffect(), DiffAction():
                        is_sound_patch_found = True
                        break
                    case _, _:
                        is_sound_patch_found = False
                        continue

            if is_sound_patch_found:
                break

    def runner_from_shell(
        self,
    ):
        @click.command()
        @click.option(
            "--detection-path",
            "-d",
            required=True,
            type=click.Path(exists=True, file_okay=True, dir_okay=False),
        )
        @click.option(
            "--challenge-working-directory",
            "-w",
            required=True,
            type=click.Path(exists=True, file_okay=False, dir_okay=True),
        )
        @click.option(
            "--output-directory",
            "-o",
            required=True,
            type=click.Path(exists=True, file_okay=False, dir_okay=True),
        )
        def _(
            detection_path: str,
            challenge_working_directory: str,
            output_directory: str,
        ):
            detection = Detection.from_toml(Path(detection_path))

            challenge_project = ChallengeSource.from_detection(
                detection, Path(challenge_working_directory)
            )

            self.run(detection, challenge_project, Path(output_directory))

        return _
