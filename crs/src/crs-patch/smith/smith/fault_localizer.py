import logging
import os
from typing import List, Type, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path

import git
from unidiff import PatchSet, Hunk
from typing_extensions import override

from .challenge import Challenge
from .bug import Location, Bug
from .crash_analyzer import CrashReport, Frame

logger = logging.getLogger(__name__)

@dataclass
class Fault:
    locations: List[Location]

    def to_json(self) -> Any:
        return [location.to_json() for location in self.locations]

    @staticmethod
    def from_json(json: Any) -> "Fault":
        return Fault([Location.from_json(location) for location in json])


def _deduplicate(dup: List) -> List:
    unique = []
    for item in dup:
        if item not in unique:
            unique.append(item)
    return unique

class FaultLocalizer(ABC):
    def __init__(self, challenge: Challenge, bug: Optional[Bug] = None,
                 top_k: int = -1, use_k: int = -1):
        self._challenge = challenge
        self._bug = bug if bug else challenge.bug
        self._top_k = top_k
        self._use_k = use_k

    @staticmethod
    @abstractmethod
    def name() -> str:
        pass

    def localize(self) -> List[Fault]:
        faults = self._localize()
        candidates = [fault.locations for fault in faults]
        self._bug.add_candidates(candidates)
        return faults

    @abstractmethod
    def _localize(self) -> List[Fault]:
        pass

    def _select(self, faults: List[Fault]) -> List[Fault]:
        if self._use_k != -1:
            return self._select_by_use_k(faults)

        if self._top_k != -1:
            return self._select_by_top_k(faults)

        return faults

    def _select_by_use_k(self, faults: List[Fault]) -> List[Fault]:
        if len(faults) > self._use_k:
            return [faults[self._use_k]]
        else:
            return []

    def _select_by_top_k(self, faults: List[Fault]) -> List[Fault]:
        return faults[:self._top_k]


    def _convert_locations_to_faults_with_n(self, locations: List[Location], n: int) -> List[Fault]:
        faults: List[Fault] = []
        if len(locations) == 0:
            return faults
        for i in range(0, len(locations), n):
            faults.append(Fault(locations[i:i+n]))
        return faults


class StackTraceFaultLocalizer(FaultLocalizer):
    @staticmethod
    def name() -> str:
        return 'stacktrace'

    @override
    def _localize(self) -> List[Fault]:
        cr = self._get_crash_report()
        if cr is None or len(cr.stacks) == 0:
            return []
        return self.localize_with_crash_report(cr)

    def _get_crash_report(self) -> Optional[CrashReport]:
        return self._challenge.get_crash_report()

    def _convert_locations_to_faults(self, locations: List[Location]) -> List[Fault]:
        return self._convert_locations_to_faults_with_n(locations, 1)

    def localize_with_crash_report(self, cr: CrashReport) -> List[Fault]:
        locations = self._get_locations_from_crash_report(cr)
        faults = self._convert_locations_to_faults(locations)
        return self._select(faults)

    def _get_locations_from_crash_report(self, cr: CrashReport) -> List[Location]:
        if len(cr.stacks) == 0:
            return []

        first_stack = cr.stacks[0]
        frames = first_stack.frames[first_stack.sanitizer_index:]
        frames = _deduplicate(frames)
        return [self._convert_frame_to_location(frame) for frame in frames]

    def _convert_frame_to_location(self, frame: Frame) -> Location:
        return Location(Path(os.path.normpath(frame.file)), frame.line, frame.line)


class StackTraceFullFaultLocalizer(StackTraceFaultLocalizer):
    DEFAULT_TOP_K = 5

    def __init__(self, challenge: Challenge, bug: Optional[Bug] = None,
                 top_k: int = DEFAULT_TOP_K, use_k: int = -1):
        super().__init__(challenge, bug, top_k, use_k)

    @staticmethod
    def name() -> str:
        return 'stacktrace_full'

    def _convert_locations_to_faults(self, locations: List[Location]) -> List[Fault]:
        # XXX: This is so strange. We should fix this.
        if self._top_k != -1:
            locations = locations[:self._top_k]

        return self._convert_locations_to_faults_with_n(locations, len(locations))


class BICFaultLocalizer(FaultLocalizer):
    @staticmethod
    def name() -> str:
        return 'bic'

    @override
    def _localize(self) -> List[Fault]:
        git_repo = git.Repo(self._challenge.src_dir)
        commit_hash = self._bug.bic_hash
        assert commit_hash is not None, 'BIC hash is required for BIC fault localization'
        return self.localize_with_bic(git_repo, commit_hash)

    def localize_with_bic(self, git_repo: git.Repo, commit_hash: str) -> List[Fault]:
        locations = self._get_diff_locations(git_repo, commit_hash)
        faults = self._convert_locations_to_faults(locations)
        return self._select(faults)

    def _convert_locations_to_faults(self, locations: List[Location]) -> List[Fault]:
        return self._convert_locations_to_faults_with_n(locations, 1)

    def _is_supported_file(self, file: Path) -> bool:
        supported_extensions = ['.c', '.cc', '.cpp', '.h', '.hpp', '.hh', '.java', '.in']
        return file.suffix in supported_extensions

    def _get_hunk_location(self, hunk: Hunk, source_file: Path) -> Location:
        start_line = hunk.source_start
        end_line = hunk.source_start + hunk.source_length - 1

        # More precise way to find the fault location
        return Location(source_file, start_line, end_line)

    def _get_diff_locations(self, git_repo: git.Repo, commit_hash: str) -> List[Location]:
        uni_diff_text = git_repo.git.diff(commit_hash + "^", commit_hash,
                                    ignore_blank_lines=True,
                                    ignore_space_at_eol=True)
        patch_set = PatchSet(uni_diff_text)
        locations = []

        for patch in patch_set:
            source_file = Path(git_repo.working_dir) / patch.path
            if not self._is_supported_file(source_file):
                continue

            for hunk in patch:
                loc = self._get_hunk_location(hunk, source_file)
                locations.append(loc)

        return locations


class BICFullFaultLocalizer(BICFaultLocalizer):
    @staticmethod
    def name() -> str:
        return 'bic_full'

    def _convert_locations_to_faults(self, locations: List[Location]) -> List[Fault]:
        return self._convert_locations_to_faults_with_n(locations, len(locations))


AVAILABLE_FAULT_LOCALIZERS = [
    StackTraceFaultLocalizer,
    StackTraceFullFaultLocalizer,
#     BICFaultLocalizer,
    BICFullFaultLocalizer,
]

def get_available_fault_localizers() -> List[str]:
    return [fl.name() for fl in AVAILABLE_FAULT_LOCALIZERS]

def get_fault_localizer(name: str) -> Type[FaultLocalizer]:
    for fl in AVAILABLE_FAULT_LOCALIZERS:
        if fl.name() == name:
            return fl
    raise ValueError(f'Unknown fault localizer: {name}')
