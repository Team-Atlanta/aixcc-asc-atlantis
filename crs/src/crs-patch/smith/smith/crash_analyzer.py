import logging
import json
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING
from typing_extensions import override

from smith.code_analyzer import CCodeAnalyzer

from .runner import TestResult

if TYPE_CHECKING:
    from .challenge import Challenge

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Frame:
    func_name: str
    file: str
    line: int

    @staticmethod
    def from_json(obj: Dict) -> "Frame":
        return Frame(obj['func_name'], obj['file'], obj['line'])

    def to_json(self) -> Dict:
        return {
            'func_name': self.func_name,
            'file': self.file,
            'line': self.line
        }

@dataclass(frozen=True)
class CrashStack:
    frames: List[Frame]
    sanitizer_index: int

    @staticmethod
    def from_json(obj: Dict) -> "CrashStack":
        frames = list(map(Frame.from_json, obj['frames']))
        return CrashStack(frames, obj['sanitizer_index'])

    def to_json(self) -> Dict:
        return {
            'frames': list(map(Frame.to_json, self.frames)),
            'sanitizer_index': self.sanitizer_index
        }

@dataclass(frozen=True)
class CrashReport:
    stacks: List[CrashStack]

    @staticmethod
    def from_json(obj: Dict) -> "CrashReport":
        stacks = list(map(CrashStack.from_json, obj['stacks']))
        return CrashReport(stacks)

    def to_json(self) -> Dict:
        return {
            'stacks': list(map(CrashStack.to_json, self.stacks))
        }

class CrashAnalyzer(ABC):
    def __init__(self, challenge: "Challenge", no_cache=False):
        self._challenge = challenge
        self._no_cache = no_cache
        self._make_output_dir()

    def _make_output_dir(self):
        self._get_crash_report_path()\
            .parent.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def _is_frame(self, line: bytes) -> bool:
        pass

    @abstractmethod
    def _get_frame(self, line: bytes) -> Optional[Frame]:
        pass

    @abstractmethod
    def _find_sanitizer_index(self, frames: List[Frame]) -> int:
        pass

    def _get_crash_report_path(self) -> Path:
        h = self._challenge.get_request_hash()
        return self._challenge.cache_dir / f'crash_reports/crash-{h}.json'

    def _get_raw_call_stacks(self, crash_log: bytes) -> List[List[bytes]]:
        # Crash log would look like this:
        #   [frame, frame, frame] -> ... [frame, frame, frame] -> ...
        # First, we need to split them into a set of raw stack
        lines = []
        for idx, line in enumerate(crash_log.splitlines()):
            if self._is_frame(line):
                lines.append((idx, line))

        # From given calltrace_lines, group them by calltrace.
        # A calltrace is a group of consecutive calltrace lines.
        grouped = groupby(enumerate(lines), lambda x: x[0] - x[1][0])
        return [[entry[1] for _, entry in group] for _, group in grouped]

    def _get_frames(self, lines: List[bytes]) -> List[Frame]:
        frames = []
        for line in lines:
            frame = self._get_frame(line)
            if frame is not None:
                frames.append(frame)
        return frames

    def _get_call_stack(self, rc: List[bytes]) -> Optional[CrashStack]:
        frames = self._get_frames(rc)
        if len(frames) != 0:
            sanitizer_index = self._find_sanitizer_index(frames)
            return CrashStack(frames, sanitizer_index)
        else:
            return None

    def _get_call_stacks(self, rcs: List[List[bytes]]) -> List[CrashStack]:
        call_stacks = []
        for rc in rcs:
            call_stack = self._get_call_stack(rc)
            if call_stack is not None:
                call_stacks.append(call_stack)
        return call_stacks

    def get_crash_log(self) -> bytes:
        output_dir = self._challenge.get_output_dir() / 'crash_log'
        output_dir.mkdir(parents=True, exist_ok=True)
        crash_log = self._generate_crash_log(output_dir)
        return crash_log

    def _generate_crash_log(self, output_dir: Path) -> bytes:
        res, _msg = self._challenge.perform_security_test(output_dir)
        assert res == TestResult.FAILURE, 'Security test should fail'
        stdout = (output_dir / 'security_test.stdout').read_bytes()
        stderr = (output_dir / 'security_test.stderr').read_bytes()
        return stdout + b'\n' + stderr

    def _resolve_project_path(self, file_path: Path) -> Optional[Path]:
        parts = file_path.parts
        for i in range(len(parts)):
            resolved_path = self._challenge.src_dir / Path(*parts[i:])
            resolved_path = resolved_path.resolve()
            if resolved_path.exists():
                return resolved_path
        return None

    def is_analyzed(self) -> bool:
        return self._get_crash_report_path().exists()

    def _load_crash_report(self) -> CrashReport:
        if self._no_cache:
            return self._create_crash_report()

        logger.debug('Loading crash report from %s', self._get_crash_report_path())
        with open(self._get_crash_report_path(), 'r') as f:
            return CrashReport.from_json(json.load(f))

    def _save_crash_report(self, cr: CrashReport) -> None:
        if self._no_cache:
            return

        with open(self._get_crash_report_path(), 'w') as f:
            json.dump(cr.to_json(), f, indent=4)

    def get_crash_report(self) -> CrashReport:
        if not self.is_analyzed():
            self.analyze()

        return self._load_crash_report()

    def _create_crash_report(self) -> CrashReport:
        crash_log = self.get_crash_log()
        rcs = self._get_raw_call_stacks(crash_log)
        call_stacks = self._get_call_stacks(rcs)

        if len(call_stacks) == 0:
            logger.warning('No call stack found in the crash log')

        return CrashReport(call_stacks)

    def analyze(self) -> None:
        if self.is_analyzed():
            return

        cr = self._create_crash_report()
        self._save_crash_report(cr)

class DummyCrashAnalyzer(CrashAnalyzer):
    # This is a dummy crash analyzer that does not analyze the crash log
    # It is used when the challenge only relies on crash log without analyzing it
    @override
    def _is_frame(self, line: bytes) -> bool:
        return False

    @override
    def _get_frame(self, line: bytes) -> Optional[Frame]:
        return None

    @override
    def _find_sanitizer_index(self, frames: List[Frame]) -> int:
        return 0

class KernelCrashAnalyzer(CrashAnalyzer):
    KASAN_FRAME_REGEX = re.compile(rb'\[[^\]]*\]  (.+)\+0x([0-9a-f]+)\/0x([0-9a-f]+)$')

    def __init__(self, challege: "Challenge", no_cache=False):
        super().__init__(challege, no_cache)
        self._symbol2addr: Dict[str, int] = {}

    def _load_vmlinux_symbol_table(self):
        vmlinux_o = self._challenge.build_src_dir / 'vmlinux.o'
        logger.info("Loading symbol table from vmlinux.o: %s", vmlinux_o)

        if not vmlinux_o.exists():
            logger.warning('vmlinux.o does not exists: %s', vmlinux_o)
            return None

        proc = subprocess.check_output(
            ['readelf', '-s', str(vmlinux_o)],
            text=True
        )

        for line in proc.splitlines():
            m = re.match(r"^\s*\d+: ([0-9a-f]+)\s+\d+ \w+\s+\w+\s+\w+\s+.+ (.+)?$", line)
            if m and m.group(2):
                self._symbol2addr[m.group(2)] = int(m.group(1), 16)
                # logger.info("Symbol: %s -> 0x%x", m.group(2), symbol2addr[m.group(2)])

    def _get_raw_call_stacks(self, crash_log: bytes) -> List[List[bytes]]:
        # Some information (e.g., possible circular locking dependency detection) can
        # be printed before the KASAN stacktrace with same format. To avoid parsing
        # them as KASAN stacktrace, we start parsing the crash log from 'BUG:' line.
        if b'BUG:' in crash_log:
            crash_log = crash_log[crash_log.index(b'BUG:'):]

        return super()._get_raw_call_stacks(crash_log)

    def _is_frame(self, line: bytes) -> bool:
        return bool(self.KASAN_FRAME_REGEX.search(line))

    def _create_frame(self, func_name: str, binary_offset: int) -> Optional[Frame]:
        if not self._symbol2addr:
            logger.warning('Symbol table is not loaded')
            return None

        if func_name not in self._symbol2addr:
            return None

        addr = self._symbol2addr[func_name]

        output = subprocess.check_output(
            ['addr2line', '-e', 'vmlinux.o', hex(addr + binary_offset - 1)],
            text=True,
            cwd=self._challenge.build_src_dir
        ).strip()

        if output == '??:?':
            logger.warning('Failed to resolve address: %s + 0x%x', func_name, binary_offset)

        m = re.match(r'^(.+):(\d+)$', output)
        if m is None:
            return None

        file        = self._resolve_project_path(Path(m.group(1)))
        line_number = int(m.group(2))

        if file is None:
            return None

        return Frame(func_name, str(file), line_number)

    def _get_frame(self, line: bytes) -> Optional[Frame]:
        logger.debug("Parsing KASAN frame: %s", line)
        m = self.KASAN_FRAME_REGEX.search(line)
        assert m is not None

        func_name       = m.group(1).decode()
        binary_offset   = int(m.group(2), 16)

        return self._create_frame(func_name, binary_offset)

    def _get_call_stacks(self, rcs: List[List[bytes]]) -> List[CrashStack]:
        # We only use the first call stack for KASAN
        rcs = rcs[:1]
        self._load_vmlinux_symbol_table()
        return super()._get_call_stacks(rcs)

    def _is_sanitizer_frame(self, frame: Frame) -> bool:
        if frame.func_name.startswith('kasan_') or 'kasan' in Path(frame.file).parts:
            return True

        if frame.func_name.startswith('ubsan_'):
            return True

        return False

    def _find_sanitizer_index(self, frames: List[Frame]) -> int:
        for i, sf in reversed(list(enumerate(frames))):
            if self._is_sanitizer_frame(sf):
                return i + 1

        # Default to the last frame
        return 0

class JazzerCrashAnalyzer(CrashAnalyzer):
    BASEPATH = [Path("core/src/main/java"), Path("src/main/java")]

    @override
    def get_crash_log(self) -> bytes:
        crash_log = super().get_crash_log()
        try:
            crash_log = crash_log[crash_log.index(b" == Java Exception: "):]
            crash_log = crash_log[:crash_log.index(b" == libFuzzer crashing input ==")]
        except ValueError:
            crash_log = b""
        return crash_log

    def _is_frame(self, line: bytes) -> bool:
        return line.strip().startswith(b"at ")

    def _get_frame(self, line: bytes) -> Optional[Frame]:
        m = re.match(rb"^at (.+)\((.+)\.java:(\d+)\)$", line.strip())
        if m is None:
            return None
        method = m.group(1).decode()
        file_name = m.group(2).decode()
        path_list = method.split(".")
        if len(path_list) < 3:
            return None

        func_name = path_list.pop()
        if not path_list.pop().startswith(file_name):
            return None
        file_name += ".java"

        file = None
        for base in self.BASEPATH:
            path = base
            for p in path_list:
                path = path / p
            file = self._resolve_project_path(path / file_name)
            if file is not None:
                break

        if file is None:
            return None

        line_number = int(m.group(3))

        return Frame(func_name, str(file), line_number)

    def _find_sanitizer_index(self, frames: List[Frame]) -> int:
        # Default to the last frame
        return 0

class UserlandCCrashAnalyzer(CrashAnalyzer):
    ASAN_FRAME_WEAK_REGEX = re.compile(rb'^\s+#\d+ 0x[0-9a-f]+ in (.+)$')
    ASAN_FRAME_REGEX      = re.compile(rb'^\s+#\d+ 0x[0-9a-f]+ in (.+) ([^:]+):(\d+)(?::\d+)?$')
    UBSAN_FRAME_REGEX     = re.compile(rb'^([^:]+):(\d+):(\d+): runtime error: .+$')

    def _is_frame(self, line: bytes) -> bool:
        # We use a weak regex for ASAN frame because there's a case
        # where line/column is not available
        return (
            bool(self.ASAN_FRAME_WEAK_REGEX.match(line)) or
            bool(self.UBSAN_FRAME_REGEX.match(line))
        )

    def _get_asan_frame(self, line: bytes) -> Optional[Frame]:
        m = self.ASAN_FRAME_REGEX.match(line)
        if m is None:
            return None

        func_name   = m.group(1).decode()
        file        = self._resolve_project_path(Path(m.group(2).decode()))
        line_number = int(m.group(3))

        if file is None:
            return None

        return Frame(func_name, str(file), line_number)

    def _get_func_name(self, file: Path, line_number: int) -> str:
        code_analyzer = CCodeAnalyzer(file, []) # No compile_args
        span = (line_number, line_number)
        try:
            func_info = code_analyzer.find_function(span)
        except Exception: # pylint: disable=broad-exception-caught
            return ""
        return func_info.name or ""

    def _get_ubsan_frame(self, line: bytes) -> Optional[Frame]:
        m = self.UBSAN_FRAME_REGEX.match(line)
        if m is None:
            return None

        file        = self._resolve_project_path(Path(m.group(1).decode()))
        line_number = int(m.group(2))

        if file is None:
            return None

        func_name = self._get_func_name(file, line_number)
        return Frame(func_name, str(file), line_number)

    def _get_frame(self, line: bytes) -> Optional[Frame]:
        return self._get_asan_frame(line) or self._get_ubsan_frame(line)

    def _find_sanitizer_index(self, frames: List[Frame]) -> int:
        # Default to the last frame
        return 0
