from pathlib import Path

from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.circuit.models import Circuit
from loop.framework.detection.models import Detection


def reports_of_challenge_project(
    circuit: Circuit,
    challenge_project_directory: Path,
    output_directory: Path,
    detections: list[Detection],
):
    assert all(detection.cp_name == detections[0].cp_name for detection in detections)

    for detection in detections:
        challenge_source = ChallengeSource.from_detection(
            detection, challenge_project_directory
        )

        yield circuit.run(detection, challenge_source, output_directory)
