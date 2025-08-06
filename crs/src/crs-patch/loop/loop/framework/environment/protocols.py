from pathlib import Path
from typing import Protocol

from rusty_results.prelude import Result

from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection


class EnvironmentProtocol(Protocol):
    def restore(
        self, challenge_source: ChallengeSource
    ) -> Result[tuple[str, str], Exception]: ...

    def build(
        self, challenge_source: ChallengeSource
    ) -> Result[tuple[str, str], Exception]: ...

    def patch(
        self, challenge_source: ChallengeSource, patch_file: Path
    ) -> Result[tuple[str, str], Exception]: ...

    def run_pov(
        self, challenge_source: ChallengeSource, detection: Detection
    ) -> Result[tuple[str, str], Exception]: ...

    def run_tests(
        self, challenge_source: ChallengeSource
    ) -> Result[tuple[str, str], Exception]: ...
