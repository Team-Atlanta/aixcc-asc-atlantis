from typing import TypeAlias

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

Effect: TypeAlias = (
    DumbEffect
    | CompilableEffect
    | VulnerableEffect
    | SoundEffect
    | WrongFormatEffect
    | EmptyEffect
    | UnknownErrorEffect
    | WrongPatchEffect
)
