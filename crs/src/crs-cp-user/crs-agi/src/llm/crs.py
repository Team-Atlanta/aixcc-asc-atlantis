import functools

from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path

import yaml

from loguru import logger

from .plugins import Workspace, WorkspaceTool

@dataclass
class PoVResult:
    blob: Path
    harness: str
    stdout: str
    sanitizers: [str]

    def is_crashed(self):
        return not self.caught_by() is None

    def caught_by(self):
        if hasattr(self, "__caught_by"):
            return getattr(self, "__caught_by")

        rtn = None
        for s in self.sanitizers:
            if s in self.stdout:
                rtn = s
                break
        setattr(self, "__caught_by", rtn)
        return rtn


class CRSWorkspace(Workspace):
    def __init__(self, cp, rebuild=True, root=None, delete=True):
        super().__init__(root=root, delete=delete)

        # preparing CP
        self.ln(cp, "cp")
        self.cp = self.get_path("cp")
        self.log(f"Loaded CP @{self.cp}", console=True)

        # ensure it's properly built and runnable
        if rebuild:
            self.reset_cp()
            self.run_build()
            self.run_tests()

    # NOTE. cwd() is set under "/cp"!
    def get_cwd(self):
        return self.workspace / "cp"

    def run_tests(self):
        self.run(["./run.sh", "run_tests"])

    def run_build(self):
        self.run(["./run.sh", "build"])

    def reset_cp(self):
        self.run("git reset --hard HEAD", shell=True)

    @functools.cache
    def project_yaml(self):
        with open(self.cp / "project.yaml") as fd:
            try:
                return yaml.safe_load(fd)
            except yaml.YAMLError as e:
                logger.error(f"ERROR: failed to load project.yaml: {e}")
        return {}

    @functools.cache
    def get_sanitizers(self):
        return list(self.project_yaml()["sanitizers"].values())

    def run_pov(self, blob, harness):
        (_, stdout) = self.run_with_capture(["./run.sh", "run_pov", blob, harness])
        return PoVResult(blob=Path(blob), harness=harness,
                         stdout=stdout, sanitizers=self.get_sanitizers())


class ProjectYamlPlugin(WorkspaceTool):
    name = "get_cp_project_yaml"
    description = """Read the content of `project.yaml` in CP."""

    @abstractmethod
    def run(self, **args):
        return open(self.workspace.get_path("cp/project.yaml")).read()


def get_crs_plugins(workspace):
    return [ProjectYamlPlugin(workspace)]


