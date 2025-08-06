from typing import Protocol

from loop.commons.context.models import RequiresContext
from loop.framework.action.models import Action
from loop.framework.effect.models import Effect
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
from loop.framework.seed.models import Seed
from loop.framework.wire.context import WireContext


class PickerProtocol(Protocol):
    def pick(
        self, action: Action, effect: Effect
    ) -> RequiresContext[Seed, WireContext]:
        match effect:
            case DumbEffect():
                return self.of_dumb(action, effect)
            case CompilableEffect():
                return self.of_compilable(action, effect)
            case VulnerableEffect():
                return self.of_vulnerable(action, effect)
            case SoundEffect():
                return self.of_sound(action, effect)
            case WrongFormatEffect():
                return self.of_wrong_format(action, effect)
            case EmptyEffect():
                return self.of_empty(action, effect)
            case UnknownErrorEffect():
                return self.of_unknown_error(action, effect)
            case WrongPatchEffect():
                return self.of_wrong_patch(action, effect)

    def of_dumb(
        self, action: Action, effect: DumbEffect
    ) -> RequiresContext[Seed, WireContext]: ...

    def of_compilable(
        self, action: Action, effect: CompilableEffect
    ) -> RequiresContext[Seed, WireContext]: ...

    def of_vulnerable(
        self, action: Action, effect: VulnerableEffect
    ) -> RequiresContext[Seed, WireContext]: ...

    def of_sound(
        self, action: Action, effect: SoundEffect
    ) -> RequiresContext[Seed, WireContext]: ...

    def of_wrong_format(
        self, action: Action, effect: WrongFormatEffect
    ) -> RequiresContext[Seed, WireContext]: ...

    def of_empty(
        self, action: Action, effect: EmptyEffect
    ) -> RequiresContext[Seed, WireContext]: ...

    def of_unknown_error(
        self, action: Action, effect: UnknownErrorEffect
    ) -> RequiresContext[Seed, WireContext]: ...

    def of_wrong_patch(
        self, action: Action, effect: WrongPatchEffect
    ) -> RequiresContext[Seed, WireContext]: ...
