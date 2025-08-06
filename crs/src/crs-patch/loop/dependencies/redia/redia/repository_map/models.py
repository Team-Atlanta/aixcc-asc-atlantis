from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class Tag:
    absolute_path: Path
    kind: Literal["def", "ref"]
    name: str
    start_line_index: int | None
