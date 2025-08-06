from __future__ import annotations
import logging
import glob
import json

from pathlib import Path
from enum import Enum, auto
from typing import Optional, Tuple, List
from dataclasses import dataclass

from .challenge import Challenge
from .bug import Bug
from .model import Dialog
from .prompter import Prompt, Template

logger = logging.getLogger(__name__)

class PatchResult(Enum):
    COMPILE_ERROR = auto()
    FUNCTIONAL_ERROR = auto()
    SECURITY_ERROR = auto()
    SUCCESS = auto()
    TEST_ERROR = auto() # This is for testing purposes

@dataclass(frozen=True)
class PatchOutcome():
    name: str
    result: PatchResult
    message: str

    def to_list(self) -> List:
        if self.result == PatchResult.COMPILE_ERROR:
            return [self.name, False, False, False, self.message]
        if self.result == PatchResult.FUNCTIONAL_ERROR:
            return [self.name, True, False, False, self.message]
        if self.result == PatchResult.SECURITY_ERROR:
            return [self.name, True, True, False, self.message]
        if self.result == PatchResult.SUCCESS:
            return [self.name, True, True, True, self.message]
        raise ValueError(f"Unknown PatchResult: {self.result}")

    def is_success(self) -> bool:
        return self.result == PatchResult.SUCCESS

    def is_error(self) -> bool:
        return not self.is_success()

    def is_compile_error(self) -> bool:
        return self.result == PatchResult.COMPILE_ERROR

    def is_functional_error(self) -> bool:
        return self.result == PatchResult.FUNCTIONAL_ERROR

    def is_security_error(self) -> bool:
        return self.result == PatchResult.SECURITY_ERROR

@dataclass(frozen=True)
class PatchMeta:
    model: str
    temperature: float

class PatchTrial:
    def __init__(self,
                 bug: Bug,
                 dialog: Dialog,
                 prompt: Prompt,
                 template: Template,
                 diff: str,
                 op: str,
                 meta: PatchMeta,
                 parent: Optional[PatchTrial]=None):
        self._bug = bug
        self._dialog = dialog
        self._prompt = prompt
        self._template = template
        self._diff = diff
        self._op = op
        self._meta = meta
        self._parent = parent
        self._round = 0 if parent is None else parent.round + 1

        self._id = self._gen_next_id()
        self._make_output_dir()

    def _gen_next_id(self) -> int:
        output_dir = self._bug.get_output_dir()
        return len(glob.glob(str(output_dir / 'id_*')))

    def _make_output_dir(self) -> None:
        output_dir = self._bug.get_output_dir() / self.name
        output_dir.mkdir(parents=True, exist_ok=True)
        # This is to ensure that the id is correctly generated
        assert self._gen_next_id() == self._id + 1

    def to_build_args(self, challenge: Challenge, output_dir: Path) -> Tuple[str, str]:
        diff_file = output_dir / "patch.diff"
        diff_file.write_text(self.diff)
        return (str(diff_file.resolve()), str(challenge.repo_dir))

    @property
    def id(self) -> int:
        return self._id

    @property
    def dialog(self) -> Dialog:
        return self._dialog

    @property
    def prompt(self) -> Prompt:
        return self._prompt

    @property
    def template(self) -> Template:
        return self._template

    @property
    def diff(self) -> str:
        return self._diff

    # pylint: disable=protected-access
    @staticmethod
    def spawn(parent: PatchTrial, dialog: Dialog, \
                diff: str, op: str) -> PatchTrial:
        return PatchTrial(parent._bug, dialog, parent._prompt, parent._template, \
                          diff, op, parent._meta, parent)

    def write_to_file(self, output_dir: Path, success: bool=False) -> None:
        if success:
            sound_patch_file = output_dir / "patch-sound.diff"
            sound_patch_file.write_text(self._diff)

        with open(output_dir / "raw_prompt.json", 'w') as f:
            # Removing non-dict items (ex. Message(), ChatCompletionMessageToolCall() from plugins)
            to_dump = [item for item in self._dialog.to_raw() if isinstance(item, dict)]
            f.write(json.dumps(to_dump, indent=2))

        with open(output_dir / 'prompt.txt', 'w') as f:
            f.write(self._prompt.to_string())

    @property
    def name(self) -> str:
        src = self._id if self._parent is None else self._parent._id
        return ','.join([
            f'id_{self._id:06d}',
            f'src_{src:06d}',
            f'op_{self._op}',
            f'model_{self._meta.model}',
            f'temp_{self._meta.temperature}'
        ])

    @property
    def round(self) -> int:
        return self._round
