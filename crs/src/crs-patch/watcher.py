from pathlib import Path
import asyncio
import logging

import toml


class RequestWatcher:
    def __init__(self, loop: asyncio.BaseEventLoop, queue: asyncio.Queue, requests_dir: Path):
        self._queue = queue
        self._loop = loop
        self._requests_dir = requests_dir
        self._completed = set()

    @property
    def time_wait(self) -> float:
        return 30

    @property
    def time_retry(self) -> int:
        return 1

    @property
    def max_retry(self) -> int:
        return 5
    
    async def watch(self):
        i = 0
        try:
            while True:
                logging.info(f"[watcher] Iteration {i}")
                i += 1
                for request in self._requests_dir.glob("*.toml"):
                    if request in self._completed:
                        continue
                    if not self._check_valid(request):
                        continue

                    logging.info(f"[watcher] Detect new request: {request.name}")
                    self._loop.call_soon_threadsafe(self._queue.put_nowait, request)
                    self._completed.add(request)
                await asyncio.sleep(self.time_wait)
        except Exception as e:
            logging.error("[watcher] Unexpected exception: %s", e)
            self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

    @property
    def _required_fields(self):
        return [
            "cp_name",
            "blob_file",
            "harness_id",
            "bug_introduce_commit",
            "src_dir",
            "cpv_uuid",
        ]

    def _check_valid(self, request: Path) -> bool:
        try:
            info = toml.load(request)
            return all(field in info for field in self._required_fields) \
                and (not Path(info["blob_file"]).is_absolute() or Path(info["blob_file"]).exists())
        except (toml.TomlDecodeError, FileNotFoundError):
            return False
