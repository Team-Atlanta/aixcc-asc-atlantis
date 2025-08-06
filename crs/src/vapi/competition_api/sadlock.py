from contextlib import asynccontextmanager
from pathlib import Path

from filelock import AsyncFileLock
from vyper import v


v.set_default("filelock_dir", "/file_locks")


@asynccontextmanager
async def create_async_sadlock(name: str) -> None:
    """
    SQLite has no "named lock" or "advisory lock" mechanism as in MySQL
    or PostgreSQL. A workaround is to use file locks instead (ref.
    https://github.com/ClosureTree/with_advisory_lock)
    """
    dir = Path(v.get("filelock_dir"))
    dir.mkdir(exist_ok=True)
    async with AsyncFileLock(dir / f"{name}.lock"):
        yield


async def test_and_set(name: str, new_value: bool | None = True) -> bool:
    """
    Simple mechanism for atomic test-and-set for flags using arbitrary*
    string names
    *must be valid filenames (e.g., no "/")
    """
    async with create_async_sadlock('test_and_set'):
        flag_file = Path(v.get("filelock_dir")) / f"{name}.flag"
        prev = flag_file.is_file()
        if new_value is not None:
            if new_value:
                flag_file.touch()
            else:
                flag_file.unlink()
    return prev
