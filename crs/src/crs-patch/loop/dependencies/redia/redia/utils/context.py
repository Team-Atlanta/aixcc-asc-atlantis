from typing import Callable, Generic, TypeVar

_Return = TypeVar("_Return")
_Context = TypeVar("_Context")


class RequiresContext(Generic[_Return, _Context]):
    def __init__(self, func: Callable[[_Context], _Return]) -> None:
        self.func = func

    def __call__(self, context: _Context) -> _Return:
        return self.func(context)
