from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Environment():
    output_dir: Path
    no_cache: bool = False
