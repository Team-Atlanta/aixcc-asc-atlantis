from abc import ABC, abstractmethod
from pathlib import Path
import logging
import yaml

from .common import run_command


class ChallengeProject(ABC):
    def __init__(self, base: Path, name: str):
        self._base = base
        self._name = name

    @classmethod
    def load(cls, base: Path):
        yaml_path = base / "project.yaml"
        if not yaml_path.exists():
            logging.error(f"project.yaml not found in {base}")
            return ChallengeProject(base)

        with open(yaml_path, "r") as f:
            info = yaml.safe_load(f)

        """
        for subclass in cls.__subclasses__():
            if subclass.name() == info["cp_name"]:
                return subclass(base)
        """

        return ChallengeProject(base, info["cp_name"])

    def name(self) -> str:
        return self._name

    def clone(self, path: Path) -> 'ChallengeProject':
        run_command(f"rsync -a {self._base}/. {path}")
        return ChallengeProject.load(path)

    def prepare(self):
        # TODO: cpsrc & docker related MUST NOT occur during the competition
        run_command("make cpsrc-prepare", self._base)
        # run_command("make docker-pull", self.base)
        run_command("make docker-build", self._base)
        run_command("make docker-config-local", self._base)

    def build(self) -> bool:
        run_command("./run.sh build", self._base)
        return True

    def run_tests(self) -> bool:
        run_command("./run.sh run_tests", self._base)
        return True

    def custom(self, cmd: str):
        run_command(f"./run.sh custom {cmd}", self._base)

    def add_safe_directory(self):
        yaml_path = self._base / "project.yaml"
        with open(yaml_path, "r") as f:
            project = yaml.safe_load(f)

        for src_name in project["cp_sources"]:
            src_dir = self._base / "src" / src_name
            run_command(f"git config --global --add safe.directory '{src_dir}'")


"""
class CPLinuxKernel(ChallengeProject):
    @staticmethod
    def name() -> str:
        return "linux kernel"

    def build(self) -> bool:
        stdout = run_command("./run.sh build", self._base)
        return "Kernel: arch/x86/boot/bzImage is ready" in stdout

    def run_tests(self):
        stdout = run_command("./run.sh run_tests", self._base)
        return "SUCCESS: Patched kernel passed functionality tests!" in stdout


class CPJenkins(ChallengeProject):
    @staticmethod
    def name() -> str:
        return "jenkins"


class CPUserland(ChallengeProject):
    @staticmethod
    def name() -> str:
        return "Mock CP"
"""
