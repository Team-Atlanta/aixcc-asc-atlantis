from itertools import groupby
from pathlib import Path

import click
from multiprocess.pool import Pool

from loop.framework.benchmark.functions import reports_of_challenge_project
from loop.framework.circuit.models import Circuit
from loop.framework.detection.models import Detection

_HARDCODED_CP_DIRECTORY_MAP = {
    "Mock CP": "mock-cp",
    "jenkins": "asc-challenge-002-jenkins-cp",
    "linux kernel": "challenge-001-linux-cp",
    "userland_c": "challenge-004-nginx-cp",
}


def use_runner(
    circuit: Circuit,
):

    @click.command()
    @click.argument(
        "detection-files",
        required=True,
        type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
        nargs=-1,
    )
    @click.option(
        "--challenge-projects-directory",
        "-c",
        required=True,
        type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    )
    @click.option(
        "--output-directory",
        "-o",
        required=True,
        type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    )
    def run(
        detection_files: tuple[Path],
        challenge_projects_directory: Path,
        output_directory: Path,
    ):

        detections = sorted(
            [Detection.from_toml(path) for path in detection_files],
            key=lambda x: x.cp_name,
        )

        index = 0

        while True:
            versioned_directory = Path(output_directory) / f"{index:05d}"

            if not versioned_directory.exists():
                versioned_directory.mkdir()
                break
            else:
                index += 1

        detections_by_cp_name = [
            (cp_name, list(detections))
            for cp_name, detections in groupby(detections, key=lambda x: x.cp_name)
        ]

        pool = Pool(6)

        pool.map(
            lambda cp_name_and_detection: list(
                reports_of_challenge_project(
                    circuit,
                    challenge_projects_directory
                    / _HARDCODED_CP_DIRECTORY_MAP[cp_name_and_detection[0]],
                    versioned_directory,
                    cp_name_and_detection[1],
                )
            ),
            detections_by_cp_name,
        )

    return (run,)
