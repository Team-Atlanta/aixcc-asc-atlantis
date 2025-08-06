from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import json

from typing_extensions import override
from unidiff import PatchSet # type: ignore
import toml
import yaml

from .env import Environment
from .cwe import CWE, DummyCWE, SanitizerCWE
from .bug import Location
from .challenge import (
    Challenge,
    LegacyChallenge,
    LinuxChallenge,
    CGCChallenge,
    VUL4JChallenge,
    BugscppChallenge,
    CVEChallenge,
    ArvoChallenge,
    AIxCCChallenge,
    AIxCCJenkinsChallenge,
    AIxCCLinuxChallenge,
    AIxCCUserlandCChallenge,
    ChallengeProjectName,
)
from .bug import Bug


class ChallengeType(Enum):
    CGC = auto()
    VUL4J = auto()
    BUGSCPP = auto()
    CVE = auto()
    LINUX = auto()
    ARVO = auto()
    AIXCC = auto()
    UNKNOWN = auto()

class ChallengeLoader:
    DIRECTORY_TO_TYPE = {
        'cqe': ChallengeType.CGC,
        'cfe': ChallengeType.CGC,
        'java': ChallengeType.VUL4J,
        'bugspp': ChallengeType.BUGSCPP,
        'cve': ChallengeType.CVE,
        'linux': ChallengeType.LINUX,
        'arvo': ChallengeType.ARVO,
    }

    def load(self, env: Environment, root_dir: Path, config_file: Optional[Path]) -> "Challenge":
        if config_file is None:
            config_file = self._find_config_file(root_dir)

        config = self._load_config(config_file)
        ty = self._get_type(root_dir, config)
        return self._load_by_type(env, root_dir, config, ty)

    def _find_config_file(self, root_dir: Path) -> Path:
        for filename in ['info.json', 'META.toml']:
            config_file = root_dir / filename
            if config_file.exists():
                return config_file

        raise FileNotFoundError(f"Meta file not found in {root_dir}")

    def _get_type(self, root_dir: Path, config: Dict) -> ChallengeType:
        ty = self._get_type_by_root_dir(root_dir)
        if ty is not None:
            return ty

        ty = self._get_type_by_config(config)
        if ty is not None:
            return ty

        return ChallengeType.UNKNOWN

    def _get_type_by_config(self, config: Dict) -> Optional[ChallengeType]:
        # Use 'cp_name' to determine the challenge type as aixcc
        if 'cp_name' in config:
            return ChallengeType.AIXCC
        else:
            return None

    def _get_type_by_root_dir(self, root_dir: Path) -> Optional[ChallengeType]:
        if root_dir.parent.name in self.DIRECTORY_TO_TYPE:
            return self.DIRECTORY_TO_TYPE[root_dir.parent.name]
        elif root_dir.parent.parent.name in self.DIRECTORY_TO_TYPE:
            return self.DIRECTORY_TO_TYPE[root_dir.parent.parent.name]
        else:
            return None

    def _load_config(self, config_file: Path) -> Dict:
        if config_file.suffix == '.json':
            with config_file.open() as f:
                return json.load(f)
        elif config_file.suffix == '.toml':
            with config_file.open() as f:
                return toml.load(f)
        elif config_file.suffix == '.yml':
            with config_file.open() as f:
                return yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported file type: {config_file}")

    def _load_by_type(self, env: Environment, root_dir: Path,
                      config: Dict, ty: ChallengeType) -> "Challenge":
        loader_impl = self._get_loader_impl_by_type(ty)
        return loader_impl.load(env, root_dir, config, ty)

    def _get_loader_impl_by_type(self, ty: ChallengeType) -> "ChallengeLoaderImpl":
        if ty == ChallengeType.LINUX:
            return LinuxChallengeLoaderImpl()
        elif ty == ChallengeType.AIXCC:
            return AIxCCChallengeLoaderImpl()
        else:
            return GenericChallengeLoaderImpl()


class ChallengeLoaderImpl(ABC):
    @abstractmethod
    def load(self, env: Environment, root_dir: Path,
             config: Dict, ty: ChallengeType) -> "Challenge":
        pass

class LinuxChallengeLoaderImpl(ChallengeLoaderImpl):
    @override
    def load(self, env: Environment, root_dir: Path,
             config: Dict, ty: ChallengeType) -> "Challenge":
        challenge = LinuxChallenge(env, root_dir, config)
        self._load_bugs(env, challenge, config)
        return challenge

    def _load_bugs(self, env: Environment, challenge: "LinuxChallenge", config: Dict) -> None:
        diff_file = challenge.root_dir / 'patch.diff'
        if not diff_file.exists():
            return

        cwes = self._load_cwes_from_string(config['CWE'])
        self._load_bugs_from_diff(env, challenge, diff_file, cwes)

    def _load_cwes_from_string(self, cwe_str: str) -> List[CWE]:
        if isinstance(cwe_str, str):
            # Hotfix for CWE is a single string
            # This seems a bug in info.json for cp-linux
            return [CWE.from_str(cwe_str)]
        else:
            return [CWE.from_str(cwe) for cwe in cwe_str]

    def _load_bugs_from_diff(self, env: Environment,
                             chal: "Challenge", diff_file: Path, cwes: List[CWE]) -> None:
        for i, pfile in enumerate(PatchSet.from_filename(str(diff_file))):
            bug = self._load_bug_from_diff(env, chal, i, pfile, cwes)
            chal.add_bug(bug)

    def _load_bug_from_diff(self, env: Environment, chal: "Challenge",
                            bid: int, pfile: PatchSet, cwes: List[CWE]) -> "Bug":
        locations = []

        # Temporary fix for cp-linux
        # TODO: Explain why this is needed
        linux = chal.root_dir / 'target' / 'out' / 'linux'
        src = linux / pfile.path
        if not src.exists():
            src = linux / pfile.path[pfile.path.find('/') + 1:]

        # Currently, we only consider single-hunk vulnerabilities
        assert len(pfile) == 1
        hunk = pfile[0]

        for line in hunk:
            if line.is_added or line.is_removed:
                line_no = line.target_line_no if line.is_added else line.source_line_no
                locations.append(Location(src, line_no, line_no))
                break

        return Bug(env, chal, cwes, locations, bid=bid)

class GenericChallengeLoaderImpl(ChallengeLoaderImpl):
    @override
    def load(self, env: Environment, root_dir: Path,
             config: Dict, ty: ChallengeType) -> "Challenge":
        challenge = self._create_challenge_obj_by_type(env, root_dir, config, ty)
        self._load_bugs(env, challenge, config)
        return challenge

    def _create_challenge_obj_by_type(self, env: Environment, root_dir: Path,
                                      config: Dict, ty: ChallengeType) -> "Challenge":
        if ty == ChallengeType.CGC:
            return CGCChallenge(env, root_dir, config)
        elif ty == ChallengeType.VUL4J:
            return VUL4JChallenge(env, root_dir, config)
        elif ty == ChallengeType.BUGSCPP:
            return BugscppChallenge(env, root_dir, config)
        elif ty == ChallengeType.CVE:
            return CVEChallenge(env, root_dir, config)
        elif ty == ChallengeType.ARVO:
            return ArvoChallenge(env, root_dir, config)
        elif ty == ChallengeType.UNKNOWN:
            return LegacyChallenge(env, root_dir, config)
        else:
            raise ValueError(f"Unsupported challenge type: {ty}")

    def _load_bugs(self, env: Environment, challenge: "Challenge", config: Dict) -> None:
        for i, desc in enumerate(config["bugs"]):
            bug = self._load_bug(env, challenge, i, desc)
            challenge.add_bug(bug)

    def _load_bug(self, env: Environment, chal: "Challenge", bid: int, desc: str) -> "Bug":
        cwes = self._load_cwes_from_string(desc)
        locations = self._load_locations_from_string(chal, desc)
        return Bug(env, chal, cwes, locations, bid=bid)

    def _load_cwes_from_string(self, desc: str) -> List[CWE]:
        cwes: List[CWE] = []
        for cwe in desc.split("@")[0].split(","):
            if cwe == "":
                cwes.append(DummyCWE())
            else:
                cwes.append(CWE.from_str(cwe))
        return cwes

    def _load_locations_from_string(self, chal: Challenge, desc: str) -> List[Location]:
        locations = []
        for patch_location in desc.split("@")[1].split(","):
            locations.append(Location.from_str(patch_location, chal.root_dir))
        return locations

class AIxCCChallengeLoaderImpl(ChallengeLoaderImpl):
    CPNAME_TO_CLASS = {
        ChallengeProjectName.JENKINS: AIxCCJenkinsChallenge,
        ChallengeProjectName.LINUX: AIxCCLinuxChallenge,
        ChallengeProjectName.USERLAND_C: AIxCCUserlandCChallenge,
    }

    @override
    def load(self, env: Environment, root_dir: Path,
             config: Dict, ty: ChallengeType) -> "Challenge":
        challenge = self._create_challenge_obj_by_cp_name(env, root_dir, config)
        self._load_bug(env, challenge, config)
        return challenge

    def _create_challenge_obj_by_cp_name(self, env: Environment,
                                         root_dir: Path, config: Dict) -> "Challenge":
        cp_name = ChallengeProjectName.from_str(config["cp_name"])
        if cp_name not in self.CPNAME_TO_CLASS:
            raise ValueError(f"Unsupported challenge project name: {cp_name}")

        return self.CPNAME_TO_CLASS[cp_name](env, root_dir, config)

    def _load_bug(self, env: Environment, challenge: "Challenge", config: Dict) -> None:
        assert isinstance(challenge, AIxCCChallenge)
        cwes = self._load_cwes_from_project_yaml(challenge.root_dir, challenge.sanitizer_id)
        bug = Bug(env, challenge, cwes, None, None, config["bug_introduce_commit"])
        challenge.add_bug(bug)

    def _load_project_yaml(self, root_dir: Path) -> Dict:
        project_yaml = root_dir / "project.yaml"
        return yaml.load(project_yaml.read_text(), Loader=yaml.FullLoader)

    def _load_cwes_from_project_yaml(self, root_dir: Path, sanitizer_id: str) -> List[CWE]:
        project_yaml = self._load_project_yaml(root_dir)
        sanitizers = project_yaml["sanitizers"]
        return [SanitizerCWE(sanitizers[sanitizer_id])]


### Utility functions
def load_challenge(env: Environment, root_dir: Path, config_file: Optional[Path]=None) -> Challenge:
    loader = ChallengeLoader()
    challenge = loader.load(env, root_dir, config_file)
    challenge.initialize()
    return challenge

__all__ = ['load_challenge']
