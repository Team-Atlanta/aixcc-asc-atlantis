from pathlib import Path
from typing import List, Optional
import os
import toml

from ..utils.common import run_command
from .base_runner import Runner

class LoopRunner(Runner):
    def __init__(
            self,
            cp_map: dict[str, Path],
            output_path: Path,
            runner_path: Path
        ):
        super().__init__(cp_map, output_path, runner_path)

    @property
    def name(self) -> str:
        return "loop-baseline"

    async def run(self, request_file: Path) -> List[Path]:
        request = toml.load(request_file)
        cp_path = self._cp_map[request["cp_name"]]

        output_path = self._output_path / request_file.stem
        output_path.mkdir(parents=True, exist_ok=True)
        cmd = [
            "poetry", "run", "python3", "-m", "apps.redia_baseline.app",
            "-d", str(request_file),
            "-w", str(cp_path),
            "-o", str(output_path),
        ]

        env = os.environ.copy()
        env["LITELLM_API_KEY"] = os.environ["LITELLM_KEY"]
        env["LITELLM_BASE_URL"] = os.environ["AIXCC_LITELLM_HOSTNAME"]

        run_command(" ".join(cmd), self._runner_path, env)
        return self.get_patches(output_path)
