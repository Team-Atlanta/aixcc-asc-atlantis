from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class Runner(ABC):
    _cp_map: dict[str, Path]
    _output_path: Path
    _runner_path: Path

    def __init__(
            self,
            cp_map: dict[str, Path],
            output_path: Path,
            runner_path: Path
        ):
        self._cp_map = cp_map
        self._output_path = output_path
        self._runner_path = runner_path

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def get_patches(self, output_path: Path) -> List[Path]:
        return list(output_path.glob("**/*-sound.diff"))

    @abstractmethod
    async def run(self, request_file: Path) -> List[Path]:
        pass
