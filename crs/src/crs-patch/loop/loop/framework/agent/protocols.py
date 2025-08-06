from typing import Protocol

from loop.commons.context.models import RequiresContext
from loop.framework.action.models import Action
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection
from loop.framework.seed.models import Seed
from loop.framework.wire.context import WireContext


class AgentProtocol(Protocol):
    def act(
        self, detection: Detection, challenge_source: ChallengeSource, seed: Seed
    ) -> RequiresContext[Action, WireContext]: ...

    def on_sound_effect(self) -> None: ...

    def on_not_sound_effect(self) -> None: ...
