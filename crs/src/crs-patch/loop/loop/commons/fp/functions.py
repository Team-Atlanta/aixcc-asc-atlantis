from typing import Callable, Iterable, Sequence, TypeVar

from rusty_results.prelude import Err, Ok, Result

_T = TypeVar("_T")
_U = TypeVar("_U")
_E = TypeVar("_E")


def flat_map(
    func: Callable[[_T], Iterable[_U]], iterable: Iterable[_T]
) -> Iterable[_U]:
    return (item for container in map(func, iterable) for item in container)


def procedure(
    data: Sequence[_T],
    f: Callable[[_T], Result[_U, _E]],
    last_result: Result[_U, _E] | None = None,
) -> Result[_U, _E]:
    match data:
        case []:
            assert last_result is not None, "Result should not be None"
            return last_result
        case [head, *tail]:
            match result := f(head):
                case Ok():
                    return procedure(tail, f, result)
                case Err():
                    return result
        case _:
            assert False, "Unreachable code"
