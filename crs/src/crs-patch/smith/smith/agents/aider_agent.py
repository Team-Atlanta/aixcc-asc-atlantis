import os
import logging

from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional
from typing_extensions import override

import git

from smith.lib.aider.aider import models
from smith.lib.aider.aider.coders import Coder
from smith.bug import Bug
from smith.model import (
    Dialog,
    Model,
    GPT35,
    GPT4,
    GPT4o,
    GeminiPro,
    Claude3Sonnet,
    Claude3Opus,
    Claude35Sonnet
    )
from smith.agents.base_agent import Agent

l = logging.getLogger(__name__)

class AiderAgent(Agent):
    @override
    @staticmethod
    def name() -> str:
        return "AiderAgent"

    @override
    def __init__(
        self,
        model: Model,
        bug: Bug,
        temperature: float,
        edit_format: Optional[str] = None,
        edit_single: bool = False
    ):
        self._coder = self.create_coder(model, bug, temperature, edit_format, edit_single)
        self._challenge = bug.challenge

    def get_aider_model(self, model_name: str, temperature: float):
        return models.Model(
            model=self.model_converter()[model_name],
            weak_model=None,
            require_model_info=True,
            litellm_base_url=os.environ["AIXCC_LITELLM_HOSTNAME"],
            litellm_api_key=os.environ["LITELLM_KEY"],
            temperature=temperature,
        )

    def _get_buggy_files(self, bug: Bug) -> List[Path]:
        files = []
        for location in bug.locations:
            if location.src not in files:
                files.append(location.src)
        return files

    def create_coder(
        self,
        model: Model,
        bug: Bug,
        temperature: float,
        edit_format=None,
        edit_single=False) -> Coder:
        buggy_files = self._get_buggy_files(bug)
        l.info(f"Creating coder with model: {model.name()} and buggy files: {buggy_files}")
        return Coder.create(
                main_model=self.get_aider_model(model.name(), temperature),
                edit_format=edit_format,
                fnames=buggy_files,
                git_dname=None,
                auto_commits=False,
                dirty_commits=False,
                map_tokens=0,
                stream=False,
                use_git=True, #??
                retrieve_edits=True,
                edit_single=edit_single
         )

    @override
    def query(self, message) -> None:
        while message:
            message = self._coder.send_new_user_message(message)

    @override
    def get_patch_diff(self) -> str:
        with self._apply_edits() as applied:
            if not applied:
                return ""
            repo = git.Repo(self._coder.root, search_parent_directories=True)
            paths = [Path(path) for path, _ in self._coder.edits]
            patch_diff = repo.git.diff("HEAD", paths) + "\n"
        return patch_diff

    @override
    def get_dialogs(self) -> Dialog:
        return Dialog(self._coder.format_messages())

    @override
    def model_converter(self) -> Dict[str,str]:
        return {
            GPT35.name(): "oai-gpt-3.5-turbo",
            GPT4.name(): "oai-gpt-4-turbo",
            GPT4o.name(): "oai-gpt-4o",
            GeminiPro.name(): "gemini-1.5-pro",
            Claude3Sonnet.name(): "claude-3-sonnet",
            Claude3Opus.name(): "claude-3-opus",
            Claude35Sonnet.name(): "claude-3.5-sonnet"
        }

    def _get_src_path(self, path: str) -> Path:
        return self._challenge.src_dir / path

    @contextmanager
    def _apply_edits(self):
        # XXX: This is a hack to apply edits to the source code
        originals = {}
        for path, edit in self._coder.edits:
            if not edit:
                continue

            path = self._get_src_path(path)

            if path.exists():
                original = path.read_text()
            else:
                os.makedirs(path.parent, exist_ok=True)
                original = None

            originals[path] = original
            path.write_text(edit)

        try:
            yield bool(originals)
        finally:
            for path, _ in self._coder.edits:
                path = self._get_src_path(path)
                if path not in originals:
                    continue
                original = originals[path]
                if original is not None:
                    path.write_text(original)
                else:
                    path.unlink()
