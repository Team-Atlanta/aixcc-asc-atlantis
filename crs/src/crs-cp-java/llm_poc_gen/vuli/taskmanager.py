from abc import ABC, abstractmethod
from functools import reduce
from vuli.common.decorators import consume_exc, consume_exc_method, synchronized
from vuli.common.setting import Setting
from vuli.joern.joern import Joern
from vuli.joern.resource import Resource
from vuli.storage import Storage
from vuli.tasks import (
    task_llm,
    task_blob_generation,
    task_write_result,
)
from vuli.vuln import Vuln
import collections
import itertools
import queue
import os
import threading
import time
import multiprocessing

MAX_THREADS=32
semaphore = threading.Semaphore(MAX_THREADS)

class TaskManager(ABC):
    __counter = itertools.count()

    def __init__(self, wait: int = 1):
        self.done = queue.Queue()
        self.__wait = wait
        self.__queue = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._cur_task: dict = None
        self.__flag_quit = False
        self.__thread = None
        self.start()

    def __del__(self):
        self.quit()

    def __str__(self):
        return f"queue: {self.__queue.qsize()}, done: {self.done.qsize()}, on_progress: {self._cur_task != None}"

    def add(self, task: dict):
        priority: tuple = self._priority(task) + (next(self.__counter),)
        self.__queue.put((priority, task))

    def get(self) -> dict:
        return self.__queue.get(timeout=self.__wait)[-1]

    def clear(self):
        while not self.__queue.empty():
            self.__queue.get()
        while not self.done.empty():
            self.done.get()
        self.__counter = itertools.count()
        self._clear()

    def has(self):
        return (
            (not self.__queue.empty())
            or (not self.done.empty())
            or (self._cur_task != None)
        )

    @synchronized("_lock")
    def quit(self) -> None:
        self.__flag_quit = True
        self.wait()
        self.clear()

        self.__thread = None

    def restart(self) -> None:
        self.quit()
        self.start()

    @synchronized("_lock")
    def start(self) -> None:
        self.__flag_quit = False
        if self.__thread == None:
            self.__thread = threading.Thread(target=self.__run)

        if not self.__thread.is_alive():
            self.__thread.start()

    def wait(self) -> None:
        if self.__thread == None:
            return

        self.__thread.join()

    def _clear(self) -> None:
        return

    def _priority(self, task: dict) -> tuple:
        return (0,)

    @abstractmethod
    def _handle(self, task: dict) -> None:
        pass

    def __run(self) -> None:
        while True:
            with semaphore:
                if self.__flag_quit == True:
                    return
                try:
                    task = self.get()
                    self._cur_task = task
                    self._handle(task)
                except Exception:
                    continue
                finally:
                    self._cur_task = None


class QueryError:
    __items: dict = {}

    @consume_exc_method()
    def add(self, task: dict, vulns: set[str]) -> None:
        harness_id: str = task["harness_id"]
        if harness_id in self.__items:
            self.__items[harness_id] |= vulns
        else:
            self.__items[harness_id] = vulns

    def get(self) -> dict:
        return self.__items


class JoernTaskManager(TaskManager):
    joern: Joern = None
    __resource: Resource = None
    __error: QueryError = QueryError()

    def __init__(self, resource: Resource = Resource()):
        super().__init__()
        self.__resource = resource

    def __del__(self):
        if self.joern != None:
            self.joern.close_server()

    @consume_exc_method(default={})
    def get_error(self):
        return self.__error.get()

    def run_server(
        self, cpg_path: str, script_path: str, harnesses_id: list[str], semantic: str
    ):
        process_name = f"Static Taint Analysis by Joern"
        print(f"[I] {process_name}", flush=True)

        if len(harnesses_id) == 0:
            print(f"- [I] {process_name}: Skipped (No Target Harnesses)")

        self.joern = Joern()
        if os.path.exists(cpg_path):
            print(
                f"- [I] Existing CPG will be used. If you want to rebuild it, please delete {cpg_path} and try again.",
                flush=True,
            )
        else:
            print(f"- [I] {process_name}: Build CPG", flush=True)
            self.joern.build(output=cpg_path)

        print(f"- [I] {process_name}: Run Server", flush=True)
        try:
            self.joern.run_server(cpg_path, script_path, semantic, self.__resource)
        except Exception as e:
            raise RuntimeError(f"[I] {process_name}: Failed ({str(e)})")

    def _clear(self) -> None:
        self.__error: QueryError = QueryError()

    @consume_exc_method(default=None)
    def _handle(self, task: dict) -> None:
        @consume_exc(default="")
        def create_query(harness_path: str, vulns: list[str], calldepth: int) -> str:
            harness_path: str = f'"{harness_path}"'
            prepare: list[(str, str)] = list(
                map(lambda vuln: (vuln, Vuln().get_sink(vuln)), vulns)
            )
            prepare: list[(str, str)] = list(filter(lambda x: len(x[1]) > 0, prepare))
            query: str = reduce(
                lambda y, x: f'{y} ++ run({x[1]}, harness_paths, "{x[0]}")',
                prepare,
                "List()",
            )
            query: str = (
                f"context.config.maxCallDepth={calldepth}\nval harness_paths = Set({harness_path})\nsave_report({query})"
            )
            return query

        path: str = task["path"]
        vulns: list[str] = task["vulns"]
        query: str = create_query(path, vulns, self.__resource.get_calldepth())
        print(
            f"  - [I] Joern Query: {path}, {vulns}, memory: {self.__resource.get_memory()}, timeout: {self.__resource.get_timeout()}, calldepth: {self.__resource.get_calldepth()}"
        )
        new_tasks, non_timeout = self.joern.execute_query(query, timeout=self.__resource.get_timeout())
        if non_timeout == False:
            print(f"  - [W] Joern TimeOut")
            self.__error.add(task, set(vulns))
            return

        for new_task in new_tasks:
            self.done.put(new_task)


class LLMTaskManager(TaskManager):
    __llm_response: str = "llm_response"
    __num_sanitizers: dict[str, int] = collections.defaultdict(int)
    __budget: float = 0.0
    __limit: int = 300
    __last_succeed_time: time.time = time.time()

    def __init__(
        self,
        storage: Storage,
        api_key: str,
        budget: float,
        reuse: bool,
        retry_wait: int = 10,
    ):
        super().__init__(wait=1)
        self.storage = storage
        self.api_key = api_key
        self.__budget = budget
        self.reuse = reuse
        self.__retry_wait = retry_wait

    # NOTE: This method is for test purpose so far.
    def get_budget(self) -> float:
        return self.__budget

    # NOTE: This method is for test purpose so far.
    def set_budget(self, budget: float) -> None:
        self.__budget = budget

    def set_limit(self, limit: int) -> None:
        self.__limit = limit

    @consume_exc_method((10000, 10000, 1000000))
    def _priority(self, task: dict) -> None:
        response: dict = task.get(self.__llm_response, {})
        sanitizer: str = task.get("sanitizer", "")

        num_sanitizer: int = self.__num_sanitizers[sanitizer]
        retry: int = response.get(429, 0) + response.get(500, 0)
        length: int = task.get("length", 0)

        self.__num_sanitizers[sanitizer] += 1
        return (num_sanitizer, retry, length)

    @consume_exc_method()
    def _handle(self, task: dict) -> None:
        if self.__budget <= 0.0:
            print("- [W] Budget exceeds: SKIPPED")
            return

        status_code: int = task_llm(self.storage, task, self.api_key, self.reuse)
        if status_code == 200:
            self.__clean_task(task)
            self.__budget -= task.get("cost", 0.0)
            print(f"- [I] Budget: {self.__budget}")
            self.done.put(task)
            self.__last_succeed_time = time.time()
            return

        if time.time() - self.__last_succeed_time > self.__limit:
            print(f"- [W] Time Limit: SKIPPED")
            return

        if (
            self.__update_llm_response(task, status_code) == True
            and self.__need_to_retry(task, status_code) == True
        ):
            self.add(task)
            time.sleep(self.__retry_wait)
            return

        self.__clean_task(task)

    def _clear(self) -> None:
        self.__num_sanitizers.clear()
        self.__last_succeed_time = time.time()

    @consume_exc_method(default=None, log=False)
    def __clean_task(self, task: dict) -> None:
        del task[self.__llm_response]

    @consume_exc_method(default=False)
    def __update_llm_response(self, task: dict, status_code: int) -> bool:
        if (
            status_code != 429  # RateLimit
            and status_code != 500  # Internal Server Error
        ):
            return True

        if not self.__llm_response in task or not isinstance(
            task[self.__llm_response], dict
        ):
            task[self.__llm_response] = {}

        if (
            not status_code in task[self.__llm_response]
            or not isinstance(task[self.__llm_response][status_code], int)
            or task[self.__llm_response][status_code] < 0
        ):
            task[self.__llm_response][status_code] = 1
        else:
            task[self.__llm_response][status_code] += 1
        return True

    @consume_exc_method(default=False)
    def __need_to_retry(self, task: dict, status_code: int) -> bool:
        if status_code == 429:
            return True

        if (
            status_code == 500
            and task[self.__llm_response][status_code] < Setting().num_retries
        ):
            return True

        return False


class PostLLMTaskManager(TaskManager):
    def __init__(self, storage: Storage, reuse: bool):
        super().__init__()
        self.storage = storage
        self.reuse = reuse

    @consume_exc_method()
    def _handle(self, task: dict) -> None:
        if task_blob_generation(self.storage, task, False) == False:
            return

        task_write_result(self.storage, self.storage, task)
