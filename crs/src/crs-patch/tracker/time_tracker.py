import time

from .base_tracker import Tracker


class TimeTracker(Tracker):
    def __init__(self):
        self._start = None
        self._end = None

    @property
    def name(self) -> str:
        return "time"

    def _current(self) -> float:
        return time.time()

    def start(self):
        self._start = self._current()

    def end(self):
        self._end = self._current()

    def get_value(self) -> float:
        if self._start is None or self._end is None:
            raise ValueError("start and end must be set before calling get_value")

        value = self._end - self._start
        self._start = self._end = None
        return value
