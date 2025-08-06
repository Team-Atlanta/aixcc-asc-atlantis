from functools import reduce
from vuli.cp.cp import CP
from vuli.storage import sync_blackboard, Storage
from vuli.blob.generator import PythonGenerator, Generator
from vuli.common.decorators import consume_exc
from vuli.common.setting import Setting
from vuli.common.util import field_validation
from vuli.llm.model import Model
import base64


@sync_blackboard
@consume_exc(default=0)
def task_llm(task: dict, api_key: str, reuse: bool) -> int:
    @consume_exc(default="")
    def create_process_name(name: str, task: dict) -> str:
        res: str = name

        if not "llm_response" in task:
            return res

        llm_response: dict = task["llm_response"]
        if 429 in llm_response:
            res += f" [429: {llm_response[429]}]"
        if 500 in llm_response:
            res += f" [500: {llm_response[500]}]"

        return res

    @consume_exc(default=False)
    def is_valid_prompt(prompt: any) -> bool:
        if not isinstance(prompt, list):
            return False
        for message in prompt:
            if not isinstance(message, dict):
                return False
            if not "content" in message:
                return False
            if not isinstance(message["content"], str):
                return False
        return True

    process_name = "LLM"
    if not "id" in task:
        print(f"[E] {process_name}: Unknown ID")
        return 0
    id = task["id"]
    out_field = "answer"
    max_length = 50000

    model = Model(
        api_key=api_key, n=Setting().n_response, temperature=Setting().temperature
    )
    detailed_process_name: str = create_process_name(f"{process_name} [id: {id}]", task)
    process_name = (
        detailed_process_name if len(detailed_process_name) > 0 else process_name
    )
    print(f"[I] {process_name}", flush=True)
    if not field_validation(task, ["prompt"], exception=False):
        print(f"[E] {process_name}: Precondition unsatisfied")
        return 0

    if reuse and out_field in task:
        print(f"[I] {process_name}: Reused")
        return 200

    prompt = task["prompt"]
    if is_valid_prompt(prompt) == False:
        print(f"[E] {process_name}: Invalid Prompt Format")
        return 0

    length = reduce(lambda y, x: y + len(x["content"]), task["prompt"], 0)
    task["length"] = length
    if length > max_length:
        print(f"[W] {process_name}: Skip (Prompt length exceeds)")
        return 0

    query_result: tuple[int, list[str], int] = model.query(task["prompt"])
    status_code: int = query_result[0]
    answers: list[str] = query_result[1]
    cost: float = query_result[2]

    if status_code != 200:
        print(f"[W] {process_name}: Failed (status_code: {status_code})")
    else:
        task[out_field] = answers
        task["cost"] = cost

    return status_code


@sync_blackboard
def task_blob_generation(task: dict, reuse: bool) -> bool:
    process_name = "Blob Generation"
    print(f"[I] {process_name}", flush=True)
    out_field = "blob"
    generator = PythonGenerator()

    @consume_exc(default=[])
    def get_blob(task: dict, generator: Generator) -> list[bytes]:
        return generator.generate(task["answer"], task["sanitizer"])

    if not "id" in task:
        print(f"[E] {process_name}: Unknown ID")
        return False
    id = task["id"]

    process_name = f"{process_name} [id: {id}]"
    if not field_validation(task, ["sanitizer", "answer"], exception=False):
        print(f"[E] {process_name}: Precondition unsatisfied")
        return False

    if reuse and out_field in task:
        print(f"[I] {process_name}: Reused")
        return True

    blob = get_blob(task, generator)
    if len(blob) == 0:
        print(f"[E] {process_name}: Failed")
        return False

    task[out_field] = blob
    print(f"[I] {process_name}: Done")
    return True


@sync_blackboard
def task_blob_verification(task: dict, reuse: bool):
    # NOTE: This will work only for test purpose
    process_name = "Blob Verification"
    print(f"[I] {process_name}", flush=True)
    out_field = "pov"

    @consume_exc(default=set())
    def get_pov(task: dict, blob: bytes) -> set[str]:
        return CP().run_pov(task["test_harness_id"], blob)

    if not "id" in task:
        print(f"[E] {process_name}: Unknown ID")
        return False
    id = task["id"]

    process_name = f"{process_name} [id: {id}]"
    if not field_validation(
        task, ["blob", "test_harness_id", "answer"], exception=False
    ):
        print(f"[E] {process_name}: Precondition unsatisfied")
        return False

    if reuse and out_field in task:
        print(f"[I] {process_name}: Reused")
        return True

    blobs = task["blob"]
    blobs_size = len(blobs)
    povs: dict[str, str] = {}
    for i in range(0, len(blobs)):
        sub_process_name = f"{process_name} ({i+1}/{blobs_size})"
        blob: bytes = base64.b64decode(blobs[i])

        print(f"- [I] {sub_process_name}: (blob: {blob})")
        for sanitizer_id in get_pov(task, blob):
            if sanitizer_id in povs:
                # NOTE: We will not allow duplicates when the Test Harness and
                # Sanitizer are the same, but the Blob is different.
                continue

            povs[sanitizer_id] = blobs[i]

    result: list[dict[str, str]] = list(
        map(lambda item: {"sanitizer_id": item[0], "blob": item[1]}, povs.items())
    )
    result = sorted(result, key=lambda x: x["sanitizer_id"])
    task[out_field] = result
    return len(result) > 0


@sync_blackboard
def task_write_result(storage: Storage, task: dict) -> None:
    process_name = "Write Report"
    print(f"[I] {process_name}", flush=True)

    if not "id" in task:
        print(f"[E] {process_name}: Unknown ID")
        return
    id = task["id"]

    process_name = f"{process_name} [id: {id}]"
    if not field_validation(task, ["test_harness_id", "blob"], exception=False):
        print(f"[E] {process_name}: Precondition unsatisfied")
        return

    storage.add_result(task["test_harness_id"], task["blob"])
