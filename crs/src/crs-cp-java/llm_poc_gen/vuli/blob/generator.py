from abc import ABC, abstractmethod
from functools import reduce
from itertools import chain
from vuli.blob.refiner import Refiner
from vuli.common.decorators import consume_exc
from vuli.common.setting import Setting
from vuli.vuln import Vuln
import base64
import os
import re
import subprocess
import tempfile


class Generator(ABC):
    @abstractmethod
    def generate(self, input: list[str], sanitizer: str) -> list[str]:
        pass


@consume_exc(default=[])
def collect_python_script(input: str) -> list[str]:
    pattern = r"```python\n(.*?)```"
    matches = re.findall(pattern, input, re.DOTALL)
    return matches


@consume_exc(default=b"")
def get_blob_from_python_script(
    python_script: str, sentinels: list[any], timeout: int = 90
) -> list[bytes]:
    @consume_exc(default=b"")
    def run_python_script(
        script_file_path: str, output_file_path: str, sentinel: bytes
    ) -> bytes:
        cmd = [
            Setting().python_path,
            script_file_path,
            output_file_path,
            base64.b64encode(sentinel),
        ]
        it = 0
        while True:
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                break
            except subprocess.TimeoutExpired as e:
                it = it + 1
                if it > 5:
                    raise e
                print(f"[W] run_python_script ({it}/5): {str(e)}")
        with open(output_file_path, "rb") as f:
            return f.read()

    with tempfile.NamedTemporaryFile(delete=False) as tmp_script_file:
        script_file_path = tmp_script_file.name
        tmp_script_file.write(python_script.encode())
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        temp_file_path = tmp_file.name

    try:
        sentinels: list[bytes] = [
            sentinel.encode("utf-8") if isinstance(sentinel, str) else sentinel
            for sentinel in sentinels
        ]
        blobs: list[bytes] = [
            run_python_script(script_file_path, temp_file_path, sentinel)
            for sentinel in sentinels
        ]
        blobs: list[bytes] = list(filter(lambda x: len(x) > 0, blobs))
        return blobs
    finally:
        try:
            os.remove(temp_file_path)
            os.remove(script_file_path)
        except OSError as e:
            pass


@consume_exc(default="")
def bytes_to_string(blob: bytes) -> str:
    return base64.b64encode(blob).decode("utf-8")


class PythonGenerator(Generator):
    def generate(self, input: list[str], sanitizer: str) -> list[str]:
        sentinels: list[any] = Vuln().get_sentinels(sanitizer)
        python_scripts: list[str] = chain.from_iterable(
            map(collect_python_script, input)
        )
        blobs: set[str] = set()
        for script in python_scripts:
            new_blobs: list[bytes] = get_blob_from_python_script(script, sentinels)
            blobs |= set(map(lambda blob: bytes_to_string(blob), new_blobs))
        return list(blobs)
