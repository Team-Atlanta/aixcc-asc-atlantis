from vuli.commandline import get_command_line_parser
from vuli.common.decorators import consume_exc, consume_exc_method
from vuli.common.util import field_validation, get_sort_key_from_id
from vuli.cp.cp import CP
from vuli.common.setting import Setting
from vuli.vuln import Vuln
from vuli.joern.joern import Joern
from vuli.joern.resource import Resource
from vuli.llm.prompt import Prompt
from vuli.storage import JsonStorage, Storage, sync_blackboard
from vuli.taskmanager import (
    JoernTaskManager,
    LLMTaskManager,
    PostLLMTaskManager,
    TaskManager,
)

import os
import sys
import time

ENV_LLM_API_KEY = "LITELLM_KEY"


def initialize() -> None:
    print("[I] Initialize", flush=True)

    root_dir: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    parser = get_command_line_parser()

    Setting().cp_dir = parser.cp_dir
    Setting().joern_dir = parser.joern_dir
    Setting().reuse = not parser.no_reuse

    Setting().set_llm_parameter(
        parser.n_response, parser.temperature, parser.budget, parser.limit
    )
    Setting().set_python_path(parser.python_path)
    Setting().set_root_dir(root_dir)
    Setting().set_output_dir(parser.output_dir)

    CP().load(Setting().cp_dir)
    Joern().load(Setting().joern_dir)

    harnesses = parser.harnesses
    if harnesses == None:
        harnesses = list(CP().harnesses.keys())
    else:
        harnesses = list(filter(lambda x: x in CP().harnesses, harnesses.split(",")))
    harnesses = sorted(harnesses, key=lambda x: get_sort_key_from_id(x))
    Setting().harnesses = harnesses
    if len(Setting().harnesses) == 0:
        raise RuntimeError("No Harness Specified")


def joern_planning(storage: Storage, reuse: bool) -> list[str]:
    @consume_exc(default="")
    def task_to_harness_id(task: dict) -> str:
        return task["test_harness_id"]

    process_name = f"Joern Planning"
    print(f"[I] {process_name}", flush=True)

    reused_harnesses: list[str] = []
    if reuse == True:
        reused_harnesses = list(
            map(lambda task: task_to_harness_id(task), storage.get_tasks())
        )
        reused_harnesses = list(
            filter(
                lambda harness_id: harness_id in Setting().harnesses, reused_harnesses
            )
        )

    target_harnesses: list[str] = sorted(
        list(set(Setting().harnesses) - set(reused_harnesses)),
        key=lambda x: get_sort_key_from_id(x),
    )
    print(f"- [I] Joern Target Harnesses: {set(target_harnesses)}")
    print(f"- [I] Joern Reused Harnesses: {set(reused_harnesses)}")
    return target_harnesses


@sync_blackboard
def assign_test_harness_id(task: dict, reuse: bool = True) -> bool:
    process_name = "Assign Test Harness ID"
    print(f"[I] {process_name}", flush=True)
    out_field = "test_harness_id"
    table = CP().get_test_harness_as_path_to_id()

    @consume_exc(default="")
    def get_test_harness_id(task: dict, table: dict[str, str]):
        return table[task["test_harness_path"]]

    if not "id" in task:
        print("ID Not Found")
        return False
    id: int = task["id"]
    process_name = f"{process_name} [id: {id}]"
    print(f"[I] {process_name}")

    if not "test_harness_path" in task:
        print(f"[W] {process_name}: Fail (Unsatisfied Condition)")
        return False

    if reuse and out_field in task:
        print(f"[W] {process_name}: Skip (Reused)")
        return True

    harness_id: str = get_test_harness_id(task, table)
    if harness_id == "":
        print(f"[W] {process_name}: Fail (Fail to get Harness ID)")
        return False

    task[out_field] = harness_id
    return True


def exclude_non_target_harness_tasks(tasks: list[dict]) -> list[dict]:
    @consume_exc(default=False)
    def is_target_task(task: dict) -> bool:
        return task["test_harness_id"] in Setting().harnesses

    return list(filter(lambda x: is_target_task(x), tasks))


@sync_blackboard
def assign_prompt(task: dict, reuse: bool = True) -> bool:
    process_name = "Assign Prompt"
    print(f"[I] {process_name}", flush=True)
    out_field = "prompt"

    @consume_exc(default=[])
    def get_prompt(task: dict) -> list:
        return Prompt().generate(task["sanitizer"], task["code"])

    if not "id" in task:
        print("ID Not Found")
        return False
    id: int = task["id"]
    process_name = f"{process_name} [id: {id}]"
    print(f"[I] {process_name}")

    if field_validation(task, ["sanitizer", "code"], False) == False:
        print(f"[W] {process_name}: Fail (Unsatisfied Condition)")
        return False

    if reuse and out_field in task:
        print(f"[W] {process_name}: Skip (Reused)")
        return True

    prompt: list[str] = get_prompt(task)
    if len(prompt) == 0:
        print(f"[W] {process_name}: Fail (Fail to get Harness ID)")
        return False

    task[out_field] = prompt
    return True


@consume_exc(default=False)
def is_task_matched_id_list(task: dict, id_list: list[str]) -> bool:
    return task["test_harness_id"] in id_list


@sync_blackboard
def erase_target_tasks_in_storage(storage: Storage, harnesses_id: list[str]) -> None:
    @consume_exc(default=False)
    def has_harness_id(task: dict, harness_id: set[str]) -> bool:
        return task["test_harness_id"] in harness_id

    harnesses_id: set[str] = set(harnesses_id)
    tasks: list[dict] = storage.get_tasks()
    tasks: list[dict] = list(
        filter(lambda x: not has_harness_id(x, harnesses_id), tasks)
    )
    storage.set_tasks(tasks)


class JoernSchedule:
    __items: dict[str, set[str]] = {}

    def __init__(self, harnesses_id: list[str]):
        for harness_id in harnesses_id:
            self.__items[harness_id] = set(Vuln().get_vulns())

    def erase_all(self) -> None:
        self.__items = {}

    @consume_exc_method()
    def erase_harness_id(self, task: dict) -> None:
        del self.__items[task["test_harness_id"]]

    @consume_exc_method()
    def erase_vulns(self, harness_id: str, vulns: set[str]) -> None:
        self.__items[harness_id] -= vulns

    def get_items(self) -> dict[str, set[str]]:
        return self.__items

    def has(self) -> bool:
        return len(self.__items) > 0


def main():
    joern_task_manager: TaskManager = None
    llm_task_manager: TaskManager = None
    post_task_manager: TaskManager = None
    try:
        initialize()
        print(f"[I] Setting:\n{str(Setting())}\n")

        storage: Storage = JsonStorage(Setting().blackboard_path)
        storage.load()

        target_harnesses_id: list[str] = joern_planning(storage, Setting().reuse)
        erase_target_tasks_in_storage(storage, storage, target_harnesses_id)
        api_key = os.environ[ENV_LLM_API_KEY] if ENV_LLM_API_KEY in os.environ else ""

        joern_schedule: JoernSchedule = JoernSchedule(target_harnesses_id)
        joern_resource = Resource()


        joern_task_manager = JoernTaskManager(joern_resource)
        joern_task_manager.run_server(
            Setting().cpg_path,
            Setting().query_path,
            target_harnesses_id,
            Setting().semantic_dir,
        )
        llm_task_manager = LLMTaskManager(
            storage, api_key, Setting().budget, Setting().reuse, 10
        )
        post_task_manager = PostLLMTaskManager(storage, Setting().reuse)

        target_tasks: list[dict] = exclude_non_target_harness_tasks(storage.get_tasks())
        for task in target_tasks:
            if not is_task_matched_id_list(task, target_harnesses_id):
                task["pass"] = True
                joern_task_manager.done.put(task)

        def terminate() -> bool:
            return (
                not joern_task_manager.has()
                and not llm_task_manager.has()
                and not post_task_manager.has()
                and not joern_schedule.has()
            )

        updated: bool = False
        first: bool = True
        while True:
            updated = False
            if terminate() == True:
                break

            if not joern_task_manager.has() and joern_schedule.has():
                # TODO: Need to update about sentinels.
                error: dict[str, set[str]] = joern_task_manager.get_error()
                for harness_id, vulns in error.items():
                    joern_schedule.erase_vulns(harness_id, vulns)

                # This block is to try joern more.
                if first == True:
                    first = False
                else:
                    if joern_resource.increase() == False:
                        # This block is to stop joern.
                        joern_schedule.erase_all()

                joern_task_manager._clear()

                for harness_id, vulns in joern_schedule.get_items().items():
                    for vuln in vulns:
                        joern_task: dict = {
                            "harness_id": harness_id,
                            "path": CP().get_test_harness_path(harness_id),
                            "vulns": [vuln],
                        }
                        joern_task_manager.add(joern_task)

            if not joern_task_manager.done.empty():
                task: dict = joern_task_manager.done.get()
                if not "pass" in task:
                    storage.add_task(task)
                else:
                    del task["pass"]
                assign_test_harness_id(storage, task, Setting().reuse)
                assign_prompt(storage, task, Setting().reuse)
                joern_schedule.erase_harness_id(task)
                llm_task_manager.add(task)
                updated = True
            if not llm_task_manager.done.empty():
                task: dict = llm_task_manager.done.get()
                post_task_manager.add(task)
                updated = True

            if updated == True:
                print(f"[I] Joern Task Manager: {joern_task_manager}")
                print(f"[I] LLM Task Manager: {llm_task_manager}")
                print(f"[I] PostLLM Task Manager: {post_task_manager}")

            time.sleep(1)

        print(f"[I] Joern Task Manager: {joern_task_manager}")
        print(f"[I] LLM Task Manager: {llm_task_manager}")
        print(f"[I] PostLLM Task Manager: {post_task_manager}")

    except RuntimeError as e:
        print(f"[E] Error: {e}")
        return 1

    except KeyboardInterrupt:
        print(f"[I] Keyboard Interrupt occurs. Try to quit the program.")

    finally:
        if joern_task_manager != None:
            joern_task_manager.quit()

        if llm_task_manager != None:
            llm_task_manager.quit()

        if post_task_manager != None:
            post_task_manager.quit()


if __name__ == "__main__":
    sys.exit(main())
