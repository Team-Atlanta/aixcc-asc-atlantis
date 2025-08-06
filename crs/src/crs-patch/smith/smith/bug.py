from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING, Dict
from pathlib import Path
import re
import git

from .cwe import CWE
from .challenge import Challenge
from .language import Language, get_language
from .env import Environment

if TYPE_CHECKING:
    from .crash_analyzer import CrashStack

@dataclass
class Location:
    _src: Path
    _start: Optional[int]
    _end: Optional[int]

    def __init__(self, src: Path, start: Optional[int]=None, end: Optional[int]=None):
        self._src = src
        self._start = start
        self._end = end

    @property
    def src(self) -> Path:
        return self._src

    @property
    def start(self) -> int:
        assert self._start is not None
        return self._start

    @property
    def end(self) -> int:
        assert self._end is not None
        return self._end

    @staticmethod
    def from_str(s: str, root_dir: Path) -> "Location":
        m = re.match(r'(?P<src>[\w/\-._]+):(?P<start>\d+)(?:-(?P<end>\d+))?', s)
        if m is None:
            raise ValueError(f'invalid patch location: {s}')

        src = m.group('src')
        start = int(m.group('start'))
        end = int(m.group('end') or start)

        src = root_dir / src

        return Location(src, start, end)

    def to_json(self) -> Dict:
        return {'src': str(self.src), 'start': self.start, 'end': self.end}

    @staticmethod
    def from_json(json: Dict) -> "Location":
        return Location(Path(json['src']), json['start'], json['end'])

Locations = List[Location]

@dataclass
class Bug:
    _id: int
    _challenge: Optional["Challenge"]
    _cwes: List[CWE]
    _locations: Optional[Locations]
    _fault_candidates: List[Locations]
    _bic_hash: Optional[str]

    def __init__(self, env: Environment,
                 challenge: Challenge,
                 cwes: List[CWE],
                 locations: Optional[Locations] = None,
                 bid: Optional[int] = None,
                 bic_hash: Optional[str] = None):
        self._env = env
        self._challenge = challenge
        self._cwes = cwes
        self._locations = locations
        self._fault_candidates = []
        self._id = bid if bid is not None else 0
        self._bic_hash = bic_hash # bug introduce commit hash

    @property
    def id(self) -> int:
        return self._id

    @property
    def start(self) -> int:
        assert self._locations is not None
        return self._locations[0].start

    @property
    def end(self) -> int:
        assert self._locations is not None
        return self._locations[0].end

    @property
    def src(self) -> Path:
        assert self._locations is not None
        return self._locations[0].src

    @property
    def bic_hash(self) -> Optional[str]:
        return self._bic_hash

    @property
    def name(self) -> str:
        if len(self.challenge.bugs) == 1:
            return f'{self.challenge.name}'
        else:
            return f'{self.challenge.name}_{self.id}'

    @property
    def challenge(self) -> Challenge:
        assert self._challenge is not None
        return self._challenge

    @property
    def locations(self) -> Locations:
        assert self._locations is not None
        return self._locations

    @property
    def cwes(self) -> List[CWE]:
        return self._cwes

    def get_language(self) -> Language:
        return get_language(self.src)

    def get_output_dir(self) -> Path:
        return self._env.output_dir

    def get_bic_diff(self) -> Optional[str]:
        if self._bic_hash is None:
            return None

        if self._challenge is None or self._challenge.src_dir is None:
            return None

        git_repo = git.Repo(self._challenge.src_dir)
        commit_hash = self._bic_hash

        return git_repo.git.diff(commit_hash + '^', commit_hash)

    def add_candidates(self, candidates: List[List[Location]]) -> bool:
        if len(candidates) > 0:
            self._fault_candidates = candidates
            return self.switch_to_next_candidate(False)
        else:
            return False

    def switch_to_next_candidate(self, force: bool=True) -> bool:
        if len(self._fault_candidates) == 0:
            return False

        if force or self._locations is None:
            self._locations = self._fault_candidates.pop(0)
        return True
