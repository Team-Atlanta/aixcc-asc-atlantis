import requests
import os
import time

from .base_tracker import Tracker


class CostTracker(Tracker):
    def __init__(self):
        self._start = None
        self._end = None

    @property
    def name(self) -> str:
        return "cost"

    def _current(self) -> float:
        while True:
            keys = requests.get(
                os.environ["AIXCC_LITELLM_HOSTNAME"] + "/spend/keys",
                headers={
                    "Authorization": "Bearer " + os.environ["LITELLM_KEY"]
                },
                timeout=10  # Add a timeout argument to prevent the program from hanging indefinitely
            ).json()

            if 'error' in keys:
                time.sleep(1)
            else:
                break

        for key in keys:
            if key["key_name"][-4:] == os.environ["LITELLM_KEY"][-4:]:
                return key["spend"]
        raise ValueError("Key not found")

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
