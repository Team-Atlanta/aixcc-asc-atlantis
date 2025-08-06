from pathlib import Path

from rusty_results.prelude import Err, Ok, Result

from loop.commons.interaction.exceptions import CommandInteractionError
from loop.commons.interaction.functions import run_command
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection
from loop.framework.environment.exceptions import (
    ChallengeBuildFailedError,
    ChallengePoVFoundError,
    ChallengeTestFailedError,
    ChallengeWrongPatchError,
)
from loop.framework.environment.protocols import EnvironmentProtocol


class DefaultEnvironment(EnvironmentProtocol):

    def restore(self, challenge_source: ChallengeSource):
        return run_command(
            (
                f"git restore --source=HEAD :/",
                challenge_source.challenge_project_directory
                / challenge_source.source_directory,
            )
        )

    def build(
        self, challenge_source: ChallengeSource
    ) -> Result[tuple[str, str], Exception]:
        match result := run_command(
            (
                f"./run.sh -x build",
                challenge_source.challenge_project_directory,
            )
        ):
            case Ok():
                return result
            case Err(CommandInteractionError(stderr)):
                return Err(ChallengeBuildFailedError(stderr))
            case Err(e):
                assert False, f"Unreachable code: {e}"

    def patch(
        self, challenge_source: ChallengeSource, patch_file: Path
    ) -> Result[tuple[str, str], Exception]:
        match result := self.restore(challenge_source).and_then(
            lambda _: run_command(
                (
                    f"./run.sh -x build {patch_file} {challenge_source.key}",
                    challenge_source.challenge_project_directory,
                )
            )
        ):
            case Ok():
                return result
            case Err(CommandInteractionError(stderr)):
                return Err(ChallengeWrongPatchError(stderr))
            case Err(e):
                assert False, f"Unreachable code: {e}"

    def run_pov(
        self, challenge_source: ChallengeSource, detection: Detection
    ) -> Result[tuple[str, str], Exception]:
        match result := run_command(
            (
                f"./run.sh -x run_pov {detection.blob_file} {challenge_source.harness_name}",
                challenge_source.challenge_project_directory,
            )
        ):
            case Ok((stdout, _)) if challenge_source.sanitizer_name in stdout:
                return Err(ChallengePoVFoundError(stdout))
            case Ok((_, stderr)) if challenge_source.sanitizer_name in stderr:
                return Err(ChallengePoVFoundError(stderr))
            case Ok((stdout, _)):
                return result
            case Err(
                CommandInteractionError(stdout)
            ) if challenge_source.sanitizer_name in stdout.decode():
                return Err(ChallengePoVFoundError(stdout))
            case Err(
                CommandInteractionError(stderr)
            ) if challenge_source.sanitizer_name in stderr.decode():
                return Err(ChallengePoVFoundError(stderr))
            case Err():
                return result

    def run_tests(
        self, challenge_source: ChallengeSource
    ) -> Result[tuple[str, str], Exception]:
        match result := run_command(
            (
                f"./run.sh -x run_tests",
                challenge_source.challenge_project_directory,
            )
        ):
            case Ok():
                return result
            case Err(CommandInteractionError(stderr)):
                return Err(ChallengeTestFailedError(stderr))
            case Err():
                assert False, "Unreachable code"
