from pathlib import Path
from typing import List, Optional
import logging
import toml

from ..utils.common import run_command
from .base_runner import Runner


class SmithRunner(Runner):
    def __init__(
            self,
            cp_map: dict[str, Path],
            output_path: Path,
            runner_path: Path,
            name: str = "default",
            args: List[str] = [],
        ):
        super().__init__(cp_map, output_path, runner_path)

        self._name = name
        self._args = args

    @property
    def name(self) -> str:
        return f"smith-{self._name}"

    async def run(self, request_file: Path) -> List[Path]:
        request = toml.load(request_file)
        cp_path = self._cp_map[request["cp_name"]]

        output_path = self._output_path / request_file.stem / self._name
        output_path.mkdir(parents=True, exist_ok=True)
        cmd = [
            "python3", "-m", "smith.main",
            "-t", str(cp_path),
            "-o", str(output_path),
            "-r", str(request_file),
            *self._args
        ]
        run_command(" ".join(cmd), self._runner_path)
        return self.get_patches(output_path)
