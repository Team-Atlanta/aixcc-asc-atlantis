import logging
import os
import json
import shutil
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Dict, Any, Tuple, TYPE_CHECKING, Optional
from typing_extensions import override

import yaml

from .env import Environment
from .runner import (
    Runner, CPRunner, CPLinuxRunner, CPJenkinsRunner, CPUserlandRunner, CGCRunner,
    BugscppRunner, VUL4JRunner, LegacyRunner, CVERunner, LinuxRunner, ArvoRunner,
    TestResult
)
from .snapshot import (
    SnapshotManager, Snapshot, CDebugSnapshot, AIxCCLinuxDebugSnapshot,
    AIxCCJenkinsDebugSnapshot, AIxCCUserlandCDebugSnapshot
)
from .crash_analyzer import (
    CrashReport, CrashAnalyzer, KernelCrashAnalyzer,
    JazzerCrashAnalyzer, UserlandCCrashAnalyzer, DummyCrashAnalyzer
)
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .bug import Bug


class ChallengeProjectName(Enum):
    LINUX       = auto()
    JENKINS     = auto()
    USERLAND_C  = auto()

    @staticmethod
    def from_str(name: str) -> "ChallengeProjectName":
        if name == "linux kernel":
            return ChallengeProjectName.LINUX
        elif name == "jenkins":
            return ChallengeProjectName.JENKINS
        else:
            # e.g., "Mock CP", "nginx", etc.
            return ChallengeProjectName.USERLAND_C


@dataclass(frozen=True)
class BuildInfo:
    compile_commands: Dict[str, Any]
    guest_build_dir: Path
    host_build_dir: Path


@dataclass
class Challenge(ABC):
    def __init__(self, env: Environment, root_dir: Path, config: dict):
        # TODO: Find a better way to resolve cyclic dependency
        self._env = env
        self._build_root_dir = root_dir.resolve()
        self._root_dir = root_dir.resolve()
        self._src_rel_dir = Path("")
        self._bugs: List[Any] = []
        self._build_info = None
        self._name = root_dir.name

        # Cache-related attributes
        self._config = config
        self._cache_dir = self._get_cache_dir()
        self.get_output_dir().mkdir(parents=True, exist_ok=True)

        self._runner: Optional[Runner] = None
        self._crash_analyzer: Optional[CrashAnalyzer] = None

    def initialize(self) -> None:
        self._runner = self._init_runner(self._build_root_dir, self._config)
        self._crash_analyzer = self._init_crash_analyzer()

    def _get_cache_dir(self) -> Path:
        root_dir = os.path.expanduser("~")
        challenge_dir = f'{self.name}'
        cache_dir = Path(root_dir) / '.smith/cache' / challenge_dir

        if self._env.no_cache:
            logger.debug('Cleaning cache root directory')
            shutil.rmtree(cache_dir, ignore_errors=True)

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_request_hash(self) -> str:
        h = hashlib.sha256()
        h.update(json.dumps(self._config, sort_keys=True).encode('utf-8'))
        return h.hexdigest()[:32]

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @property
    def env(self) -> Environment:
        return self._env

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def repo_dir(self) -> Path:
        return self.src_dir.relative_to(self._root_dir / "src")

    @property
    def src_dir(self) -> Path:
        return (self._root_dir / self._src_rel_dir).resolve()

    @property
    def build_root_dir(self) -> Path:
        return self._build_root_dir

    @property
    def build_src_dir(self) -> Path:
        return (self._build_root_dir / self._src_rel_dir).resolve()

    @property
    def src_rel_dir(self) -> Path:
        return self._src_rel_dir

    @property
    def build_info(self) -> Optional[BuildInfo]:
        return self._build_info

    @property
    def bugs(self) -> List["Bug"]:
        return self._bugs

    @property
    def name(self) -> str:
        return self._name

    @property
    def cwd(self) -> Path:
        return self.root_dir

    @property
    def bug(self) -> "Bug":
        assert len(self._bugs) == 1
        return self._bugs[0]

    @property
    def crash_analyzer(self) -> CrashAnalyzer:
        assert self._crash_analyzer is not None
        return self._crash_analyzer

    def set_root_dir(self, root_dir: Path) -> None:
        assert self._runner is not None
        self._root_dir = root_dir.resolve()

    def path_to_writable(self, src: Path) -> Path:
        try:
            return self.root_dir / src.relative_to(self.build_root_dir)
        except ValueError:
            logger.warning(f"Failed to convert {src} to writable path")
            return src

    def path_to_buildable(self, src: Path) -> Path:
        try:
            return self.build_root_dir / src.relative_to(self.root_dir)
        except ValueError:
            logger.warning(f"Failed to convert {src} to buildable path")
            return src

    def get_output_dir(self) -> Path:
        return self._env.output_dir

    def add_bug(self, bug: "Bug") -> None:
        self._bugs.append(bug)

    def prepare(self):
        assert self._crash_analyzer is not None
        manager = SnapshotManager(self, self._init_snapshots())
        manager.load()
        self._crash_analyzer.analyze()
        # NOTE: Should we reset the challenge after the crash analysis?

    def _is_build_mode(self, mode: str) -> bool:
        return self._root_dir.name == mode

    def get_crash_report(self) -> Optional[CrashReport]:
        assert self._crash_analyzer is not None
        return self._crash_analyzer.get_crash_report()

    # Build and test the challenge
    @abstractmethod
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        raise NotImplementedError

    def _init_snapshots(self) -> List[Snapshot]:
        return []

    def _init_crash_analyzer(self) -> CrashAnalyzer:
        return DummyCrashAnalyzer(self)

    def perform_build(self, output_dir: Path,
                      args: Optional[Tuple[str, str]]=None) -> Tuple[TestResult, str]:
        assert self._runner is not None
        return self._runner.build(output_dir, args)

    def perform_functional_test(self, output_dir: Path) -> Tuple[TestResult, str]:
        assert self._runner is not None
        return self._runner.run_tests(output_dir)

    def perform_security_test(self, output_dir: Path) -> Tuple[TestResult, str]:
        assert self._runner is not None
        return self._runner.run_pov(output_dir)

    def perform_run(self, name: str, cmd: str, output_dir: Path) -> Tuple[TestResult, str]:
        assert self._runner is not None
        return self._runner.run_command(name, cmd, output_dir)

    def git_reset(self, output_dir: Path) -> Tuple[TestResult, str]:
        return self.perform_run(
            "git-reset",
            f"git -C {self.src_rel_dir} reset --hard HEAD",
            output_dir)


class LegacyChallenge(Challenge):
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        return LegacyRunner(cwd, config)

    def _init_snapshots(self) -> List[Snapshot]:
        return []


class CChallenge(LegacyChallenge):
    @override
    def _init_snapshots(self) -> List[Snapshot]:
        return [CDebugSnapshot(self)]

class CppChallenge(LegacyChallenge):
    pass


class CGCChallenge(CChallenge):
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        return CGCRunner(cwd, config)


class VUL4JChallenge(Challenge):
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        return VUL4JRunner(cwd, config)

    @override
    def prepare(self):
        logger.info("No debug/clean build for vul4j")


class BugscppChallenge(CppChallenge):
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        return BugscppRunner(cwd, config)


class CVEChallenge(Challenge):
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        return CVERunner(cwd, config)

class LinuxChallenge(Challenge):
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        return LinuxRunner(cwd, config)

class ArvoChallenge(Challenge):
    def _init_runner(self, cwd: Path, config: dict) -> Runner:
        return ArvoRunner(cwd, config)

class AIxCCChallenge(Challenge):
    def __init__(self, env: Environment, root_dir: Path, config: dict):
        super().__init__(env, root_dir, config)
        self._cp_name = config["cp_name"]
        self._sanitizer_id = config["sanitizer_id"]
        self._src_rel_dir = Path(config.get("src_dir", "src"))

    @override
    def _init_runner(self, cwd: Path, config: Dict) -> CPRunner:
        project_config = yaml.load(
            (self.cwd / "project.yaml").read_text(),
            Loader=yaml.FullLoader
        )
        harnesses = project_config["harnesses"]
        sanitizers = project_config["sanitizers"]

        return self._init_cp_runner(Path(config["blob_file"]),
                                         harnesses[config["harness_id"]]["name"],
                                         sanitizers)

    def _init_cp_runner(self, blob_file: Path, harness_name: str, sanitizers: Dict) -> CPRunner:
        raise NotImplementedError

    @property
    def cp_name(self) -> ChallengeProjectName:
        return ChallengeProjectName.from_str(self._cp_name)

    @property
    def sanitizer_id(self) -> str:
        # TODO: Move to Bug class
        return self._sanitizer_id


class AIxCCLinuxChallenge(AIxCCChallenge):
    @override
    def _init_cp_runner(self, blob_file: Path, harness_name: str, sanitizers: Dict) -> CPRunner:
        return CPLinuxRunner(self.root_dir, blob_file, harness_name, sanitizers)

    @override
    def _init_snapshots(self) -> List[Snapshot]:
        return [AIxCCLinuxDebugSnapshot(self)]

    @override
    def _init_crash_analyzer(self) -> CrashAnalyzer:
        return KernelCrashAnalyzer(self)

class AIxCCJenkinsChallenge(AIxCCChallenge):
    @override
    def _init_cp_runner(self, blob_file: Path, harness_name: str, sanitizers: Dict) -> CPRunner:
        return CPJenkinsRunner(self.root_dir, blob_file, harness_name, sanitizers)

    @override
    def _init_snapshots(self) -> List[Snapshot]:
        return [AIxCCJenkinsDebugSnapshot(self)]

    @override
    def _init_crash_analyzer(self) -> CrashAnalyzer:
        return JazzerCrashAnalyzer(self)

class AIxCCUserlandCChallenge(AIxCCChallenge):
    @override
    def _init_cp_runner(self, blob_file: Path, harness_name: str, sanitizers: Dict) -> CPRunner:
        return CPUserlandRunner(self.root_dir, blob_file, harness_name, sanitizers)

    @override
    def _init_snapshots(self) -> List[Snapshot]:
        return [AIxCCUserlandCDebugSnapshot(self)]

    @override
    def _init_crash_analyzer(self) -> CrashAnalyzer:
        return UserlandCCrashAnalyzer(self)
