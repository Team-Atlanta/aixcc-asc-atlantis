from pathlib import Path
from tempfile import NamedTemporaryFile

from rusty_results.prelude import Err, Ok

from loop.commons.context.models import RequiresContext
from loop.commons.interaction.exceptions import CommandInteractionError
from loop.commons.logging.context_manager import logging_performance
from loop.framework.action.variants import DiffAction
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection
from loop.framework.effect.models import Effect
from loop.framework.effect.variants import (
    CompilableEffect,
    DumbEffect,
    SoundEffect,
    UnknownErrorEffect,
    VulnerableEffect,
    WrongPatchEffect,
)
from loop.framework.environment.exceptions import (
    ChallengeBuildFailedError,
    ChallengePoVFoundError,
    ChallengeWrongPatchError,
)
from loop.framework.environment.protocols import EnvironmentProtocol
from loop.framework.evaluator.protocols import EvaluatorProtocol
from loop.framework.wire.context import WireContext


class AccEvaluator(EvaluatorProtocol):

    def evaluate(
        self,
        detection: Detection,
        challenge_source: ChallengeSource,
        action: DiffAction,
        environment: EnvironmentProtocol,
    ) -> RequiresContext[Effect, WireContext]:
        def _(context: WireContext):
            patch_file = NamedTemporaryFile()

            patch_file.file.write(action.content.encode())
            patch_file.file.flush()

            with logging_performance(
                context["logger"],
                f"{context['log_prefix']}:acc-evaluator:patch",
            ):
                match environment.patch(challenge_source, Path(patch_file.name)):
                    case Ok():
                        ...
                    case Err(e):
                        match e:
                            case CommandInteractionError():
                                context["logger"].error(f"Unknown error occurred:\n{e}")
                                return UnknownErrorEffect(e)
                            case ChallengeWrongPatchError():
                                context["logger"].error(
                                    f"Failed to apply the patch:\n{e}"
                                )
                                return WrongPatchEffect(
                                    diff=open(patch_file.name).read()
                                )
                            case ChallengeBuildFailedError():
                                context["logger"].error(
                                    f"Failed to build the challenge:\n{e}"
                                )
                                return DumbEffect(
                                    diff=open(patch_file.name).read(), stderr=str(e)
                                )
                            case e:
                                context["logger"].error(f"Unknown error occurred:\n{e}")
                                return UnknownErrorEffect(e)
            with logging_performance(
                context["logger"],
                f"{context['log_prefix']}:acc-evaluator:run_tests",
            ):
                match environment.run_tests(challenge_source):
                    case Ok():
                        ...
                    case Err(e):
                        context["logger"].error(f"Failed to run tests!\n{e}")
                        return CompilableEffect()

            with logging_performance(
                context["logger"],
                f"{context['log_prefix']}:acc-evaluator:run_pov",
            ):
                match environment.run_pov(challenge_source, detection):
                    case Ok():
                        return SoundEffect()
                    case Err(e):
                        match e:
                            case ChallengePoVFoundError():
                                context["logger"].error(f"Vulnerability detected:\n{e}")
                                return VulnerableEffect(str(e))
                            case CommandInteractionError():
                                context["logger"].error(f"Failed to run PoV:\n{e}")
                                return UnknownErrorEffect(e)
                            case e:
                                context["logger"].error(f"Unknown error occurred:\n{e}")
                                return CompilableEffect()

        return RequiresContext(_)
