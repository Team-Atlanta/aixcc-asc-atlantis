from abc import ABC, abstractmethod
from functools import wraps
from vuli.common.util import get_sort_key_from_id
from vuli.common.decorators import consume_exc, consume_exc_method, synchronized
import json
import threading


@consume_exc(default=-1)
def get_id(task: dict) -> int:
    return int(task["id"])


class Storage(ABC):
    __id_set: set[int] = set()
    __id_counter: int = 1
    _tasks: list[dict] = []
    _result: dict[str, list[str]] = {}
    _lock: threading.Lock = threading.Lock()

    def load(self) -> None:
        self.set_tasks(self._load())

    @synchronized("_lock")
    def set_tasks(self, tasks: list[dict]) -> None:
        self.__id_set: set[int] = set()
        self.__id_counter: int = 1
        for task in tasks:
            self.__assign_id(task)
        self._tasks = tasks
        self._tasks = sorted(self._tasks, key=lambda x: x["id"])

    @synchronized("_lock")
    def add_task(self, task: dict) -> None:
        self.__assign_id(task)
        self._tasks.append(task)
        self._tasks = sorted(self._tasks, key=lambda x: x["id"])

    @synchronized("_lock")
    def get_tasks(self) -> list[dict]:
        return self._tasks

    @synchronized("_lock")
    def add_result(self, harness_id: str, blob: list[str]) -> None:
        if harness_id in self._result:
            self._result[harness_id] += blob
        else:
            self._result[harness_id] = blob
        self._result[harness_id] = sorted(self._result[harness_id])

    @synchronized("_lock")
    def save(self) -> None:
        self._save()

    @abstractmethod
    def _load(self) -> list[dict]:
        pass

    @abstractmethod
    def _save(self) -> None:
        pass

    def __assign_id(self, task: dict) -> None:
        if "id" in task:
            if (not isinstance(task["id"], int)) or task["id"] in self.__id_set:
                del task["id"]
            else:
                self.__id_set.add(task["id"])
                return

        while self.__id_counter in self.__id_set:
            self.__id_counter += 1

        task["id"] = self.__id_counter
        self.__id_set.add(self.__id_counter)


def sync_blackboard(func):
    @wraps(func)
    def wrapper(storage, *args, **kwargs):
        res: any = func(*args, **kwargs)
        storage.save()
        return res

    return wrapper


class JsonStorage(Storage):
    path: str = ""

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    @consume_exc_method(default=[])
    def _load(self) -> list[dict]:
        with open(self.path) as f:
            return json.load(f)["tasks"]

    def _save(self) -> None:
        result: list[dict] = list(
            map(lambda x: {"harness_id": x[0], "blob": x[1]}, self._result.items())
        )
        result: list[dict] = sorted(
            result, key=lambda x: get_sort_key_from_id(x["harness_id"])
        )
        root: dict = {"tasks": self._tasks, "result": result}
        with open(self.path, "w") as f:
            json.dump(root, f, indent=4)
