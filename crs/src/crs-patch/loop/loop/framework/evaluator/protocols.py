from typing import Protocol

from loop.commons.context.models import RequiresContext
from loop.framework.action.variants import DiffAction
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection
from loop.framework.effect.models import Effect
from loop.framework.environment.protocols import EnvironmentProtocol
from loop.framework.wire.context import WireContext


class EvaluatorProtocol(Protocol):

    def evaluate(
        self,
        detection: Detection,
        challenge_source: ChallengeSource,
        action: DiffAction,
        environment: EnvironmentProtocol,
    ) -> RequiresContext[Effect, WireContext]: ...
