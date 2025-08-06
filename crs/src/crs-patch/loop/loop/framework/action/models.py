from typing import TypeAlias

from loop.framework.action.variants import (
    DiffAction,
    RuntimeErrorAction,
    WrongFormatAction,
)

Action: TypeAlias = DiffAction | WrongFormatAction | RuntimeErrorAction
