from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeAlias

_SourceDirectory: TypeAlias = Path


@dataclass
class CodingRecipe:
    system_main_prompt: str
    system_reminder_prompt: str
    file_content_prefix: str
    response_as_git_diff: Callable[[str, _SourceDirectory], str]
