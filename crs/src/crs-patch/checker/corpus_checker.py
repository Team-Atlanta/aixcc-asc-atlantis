import argparse
import json
import logging
import subprocess
import toml
import yaml

from pathlib import Path
from random import randint, seed
from typing import List, Generator, Tuple

from ..utils.common import run_command

MIN_PRIORITY_RANK = 50
MAX_TESTSET_SIZE = 10

class CorpusChecker:
    # TODO: refactor this class
    def __init__(
            self,
            args: argparse.Namespace,
            request: Path,
            cp_map: dict[str, Path]
        ):
        self._args = args
        self._request = toml.load(request)
        self._cp_map = cp_map

        # Parsing request
        self._cp_name = self._request["cp_name"]
        self._src_dir = Path(self._request["src_dir"])
        self._cp_dir = self._args.crs_scratch / "patch" / self._cp_map[self._cp_name]
        with open(self._cp_dir / "project.yaml", "r") as f:
            self._project = yaml.safe_load(f)
        self._harness_id = self._request["harness_id"]
        self._harness_name = self._project["harnesses"][self._harness_id]["name"]
        self._sanitizer_strings = list(map(lambda s: s.encode(), self._project["sanitizers"].values()))

        # Corpus related paths
        self._corpus_dir = self._args.crs_scratch / "corpus" / self._harness_id
        self._corpus_jsonfile = self._args.crs_scratch / "corpus" / f"{self._harness_id}.json"
        try:
            self._corpus_testset = self.select_corpus_testset()
        except FileNotFoundError as e:
            logging.info(f"Couldn't select test files: {e}")
            logging.info(f"Checks on this request will be skipped")
            self._corpus_testset = []

    def _git_reset(self):
        run_command(
            cmd=f"git -C {self._src_dir} reset --hard HEAD",
            cwd=self._cp_dir
        )

    def _checkable(self) -> bool:
        if self._corpus_dir.exists():
            return True
        else:
            logging.error("Corpus directory is missing")
            return False

    def check_patches(self, patches: List[Path]) -> Tuple[bool, List[Path]]:
        if not self._checkable() or self._corpus_testset == []:
            return False, patches

        return True, [patch for patch in patches if self.check_patch(patch)]

    def select_corpus_testset(self) -> List[Path]:
        """
        Get a list of test blobs from the corpus directory based on the priority.
        """
        self._git_reset()
        # TODO: replace this build command by using utils.challenge
        run_command("./run.sh build", self._cp_dir)

        if self._corpus_jsonfile.exists():
            with open(self._corpus_jsonfile, "r") as f:
                priorities = json.load(f)
        else:
            priorities = {file: 0 for file in self._corpus_dir.iterdir()}

        sorted_files = sorted(
            [file for file in priorities if (self._corpus_dir / file).exists()],
            key=priorities.get
        )

        if len(sorted_files) > MIN_PRIORITY_RANK:
            sorted_files = sorted_files[:MIN_PRIORITY_RANK]

        selected_corpus = list(self.random_selector(sorted_files, MAX_TESTSET_SIZE))
        validated_corpus = [
            corpus 
            for corpus in selected_corpus
            if self.validate_corpus(self._corpus_dir / corpus)
        ]

        return [self._corpus_dir / file for file in validated_corpus]

    def random_selector(self, lst: List, n: int) -> Generator:
        """
        Select a random subset of test files with seed fixed to 0.
        """

        seed(0)
        for _ in range(min(len(lst), n)):
            yield lst.pop(randint(0, len(lst) - 1))

    def trigger_sanitizer(self, output: bytes) -> bool:
        """
        Check if the sanitizer is triggered.
        """
        return any(sanitizer_string in output for sanitizer_string in self._sanitizer_strings)

    def validate_corpus(self, corpus: Path) -> bool:
        """
        Checks if the corpus doesn't create any crash
        """
        try:
            output = run_command(
                cmd=f"./run.sh run_pov {corpus} {self._harness_name}",
                cwd=self._cp_dir,
                timeout=30,
                pipe_stderr=True
            )
        except subprocess.TimeoutExpired:
            return False
        return not self.trigger_sanitizer(output)

    def get_cp_source(self) -> str:
        # Check if src_dir starts with "./src"
        assert self._src_dir.is_relative_to(Path("./src"))
        return self._src_dir.relative_to(Path("./src"))

    def check_patch(self, patch: Path) -> bool:
        """
        Check if the patch is valid by running the corpus tests.
        """
        if not self._checkable():
            return True
        self._git_reset()
        # NOTE: patch path can have whitespaces
        run_command(
            cmd=f"./run.sh build '{patch}' {self.get_cp_source()}",
            cwd=self._cp_dir
        )

        valid = True
        for corpus in self._corpus_testset:
            if not self.validate_corpus(corpus):
                # At least one corpus test failed
                valid = False
                break
        run_command(
            cmd=f"git -C src/{self.get_cp_source()} apply -R '{patch}'",
            cwd=self._cp_dir
        )
        return valid
