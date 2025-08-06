import logging
import json
import os
import subprocess
import traceback
from enum import Enum

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple, Optional, Callable
from typing_extensions import override

from . import constants
from .utils import run_command

logger = logging.getLogger(__name__)

def convert_to_aixcc_action(action: str) -> Optional[str]:
    if action == "build":
        return "build"
    elif action == "functional_test":
        return "run_tests"
    elif action == "security_test":
        return "run_pov"
    else:
        return None

class TestResult(Enum):
    OK = 0
    ERROR = 1
    FAILURE = 2

class Runner(ABC):
    def __init__(self, root_dir: Path, cwd: Optional[Path]=None):
        self._root_dir = root_dir
        self._cwd = cwd if cwd else root_dir

        self._build_command = ""
        self._functional_test = ""
        self._security_test = ""
        self._check_command = ""

    @property
    def cwd(self) -> Path:
        return self._cwd

    @property
    def name(self) -> str:
        return self.cwd.name

    def _perform_test(self, name: str, command: str, output_dir: Path,
                     handler: Callable) -> Tuple[TestResult, str]:
        stdout_fp = open(output_dir / f"{name}.stdout", "wb+")
        stderr_fp = open(output_dir / f"{name}.stderr", "wb+")

        try:
            (stdout, stderr, returncode) = \
                run_command(command, self.cwd, timeout=constants.TEST_TIMEOUT)
            (stdout, stderr, returncode) = self._get_result(name, stdout, stderr, returncode)

            stdout_fp.write(stdout)
            stderr_fp.write(stderr)

            (res, failmsg) = handler(stdout, stderr, returncode)

        except Exception as e: # pylint: disable=broad-exception-caught
            res = TestResult.ERROR
            traceback.print_exc()
            failmsg = f"{name} test failed (Exception: {e})"

        return (res, failmsg)

    def _get_result(self, _name: str, stdout: bytes, stderr: bytes,
                    returncode: int) -> Tuple[bytes, bytes, int]:
        return stdout, stderr, returncode

    def build(self, output_dir: Path,
              args: Optional[Tuple[str, str]]=None) -> Tuple[TestResult, str]:
        build_command = self._build_command
        if args is not None:
            build_command += f" {args[0]} {args[1]}"

        return self._perform_test("build", build_command, output_dir, self._build_handler)

    def run_tests(self, output_dir: Path) -> Tuple[TestResult, str]:
        return self._perform_test("functional_test",
                                  self._functional_test,
                                  output_dir,
                                  self._functional_handler)

    def run_pov(self, output_dir: Path) -> Tuple[TestResult, str]:
        return self._perform_test("security_test",
                                  self._security_test,
                                  output_dir,
                                  self._security_handler)

    def run_command(self, name: str, cmd: str, output_dir: Path) -> Tuple[TestResult, str]:
        return self._perform_test(name,
                                  cmd,
                                  output_dir,
                                  self._default_handler)

    def _default_handler(self, _stdout: bytes, _stderr: bytes,
                         returncode: int) -> Tuple[TestResult, str]:
        if returncode == 0:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE, f"Return code: {returncode}")

    @abstractmethod
    def _build_handler(self, stdout: bytes,
                       stderr: bytes, returncode: int) -> Tuple[TestResult, str]:
        pass

    @abstractmethod
    def _functional_handler(
        self, stdout: bytes, stderr: bytes, returncode: int
    ) -> Tuple[TestResult, str]:
        pass

    @abstractmethod
    def _security_handler(self, stdout: bytes,
                          stderr: bytes, returncode: int) -> Tuple[TestResult, str]:
        pass

class LegacyRunner(Runner):
    def __init__(self, cwd: Path, config: dict):
        super().__init__(cwd)
        self._load_config(config)

    def _load_config(self, config: dict):
        self._build_command = config['build']
        self._functional_test = config['functional_test']
        self._security_test = config['security_test']
        self._check_command = 'echo "No check command"'

    @override
    def _build_handler(self, _stdout, stderr, returncode) -> Tuple[TestResult, str]:
        if returncode == 0:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    f"Build failed (Message: {stderr.decode('utf-8', 'ignore')})")

    @override
    def _functional_handler(self, _stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        if returncode == 0:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Functional test failed (Message: At least one test case is failed)")

    @override
    def _security_handler(self, _stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        if returncode == 0:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Security test failed (Message: At least one bug can be triggered)")

    def _validator(self, _stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        return returncode == 0, ""

class CGCRunner(LegacyRunner):
    @override
    def _load_config(self, config: dict):
        # For speed up, only test 10 test cases
        self._run = config["run"]
        self._build_command = '\n'.join([ 'make clean', f'make {self._run}' ])
        self._functional_test = f'../../bin/cgc-check.py -c 10 -sla {self._run}'
        self._security_test = f'../../bin/cgc-check.py -pov {self._run}'
        self._check_command = 'make clean && make && ./check.py'

    @override
    def _functional_handler(self, stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        try:
            results = json.loads(stdout.decode("utf-8", "ignore").splitlines()[-1])
        except IndexError:
            return (TestResult.FAILURE, "Functional test failed (Message: No test result)")

        if returncode == 0 and results[self._run]["sla"]:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Functional test failed (Message: At least one test case is failed)")

    @override
    def _security_handler(self, stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        results = json.loads(stdout.decode("utf-8", "ignore").splitlines()[-1])
        if returncode == 0 and not results[self._run]["pov"]:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Security test failed (Message: At least one bug can be triggered)")

class VUL4JRunner(LegacyRunner):
    @override
    def _load_config(self, config: dict):
        # vuln4j requires the absolute path for root_dir
        self.root_dir = self.cwd.resolve()
        self._build_command = '\n'.join([
            f'docker run -u $(id -u $USER):$(id -g $USER) '
            f'-v {self.root_dir}:{self.root_dir} '
            f'--rm bqcuongas/vul4j vul4j compile -d {self.root_dir}/src'
        ])

        self._functional_test = (f'docker run -u $(id -u $USER):$(id -g $USER) '
                                f'-v {self.root_dir}:{self.root_dir} '
                                f'--rm bqcuongas/vul4j vul4j test -d {self.root_dir}/src')

        # NOTE: security_test is not needed
        self._security_test = self._functional_test
        self._check_command = (f'docker run -u $(id -u $USER):$(id -g $USER) --rm bqcuongas/vul4j '
                              f'vul4j reproduce -i {self.root_dir.name}')

    def _load_passing_tests(self):
        with open(self.root_dir / '..' / 'scripts' / 'vul4j.json', 'r') as f:
            vul4j = json.load(f)
            results = vul4j[os.path.basename(self.root_dir)]["tests"]
            if len(results["failures"]) == 0:
                raise ValueError("No failures found")
            return set(results["passing_tests"])

    @override
    def _functional_handler(self, stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        results = json.loads(stdout.decode("utf-8", "ignore"))
        passing_tests = self._load_passing_tests()
        if returncode == 0 and passing_tests.issubset(set(results["tests"]["passing_tests"])):
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE, "At least one test case failed")

    @override
    def _validator(self, stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        results = stdout.decode("utf-8", "ignore")
        if f"The vulnerability {self.root_dir.name} has been reproduced successfully with PoV(s):" in results: # pylint: disable=line-too-long
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE, "The vulnerability has not been reproduced")

    @override
    def _security_handler(self, stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        results = json.loads(stdout.decode("utf-8", "ignore"))
        if returncode == 0 and len(results["tests"]["failures"]) == 0:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE, "At least one test case failed")

class BugscppRunner(LegacyRunner):
    @override
    def _build_handler(self, _stdout, stderr, returncode) -> Tuple[TestResult, str]:
        if returncode != 0:
            return (TestResult.FAILURE,
                    f"Build failed (Message: {stderr.decode('utf-8', 'ignore')})")

        if not (self.cwd / "src" / "DPP_BUILD_SUCCESS").exists():
            return (TestResult.FAILURE, "Build failed (Message: DPP_BUILD_SUCCESS is not found)")

        return (TestResult.OK, "")

class CVERunner(LegacyRunner):
    def __init__(self, cwd: Path, config: dict):
        super().__init__(cwd, config)

        os.environ["ASAN_OPTIONS"] = "abort_on_error=1"
        os.environ["UBSAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1"

    def _security_handler(self, _stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        if returncode != 128 + 6:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Security test failed (Message: At least one bug can be triggered)")

class LinuxRunner(LegacyRunner):
    @override
    def _load_config(self, config: dict):
        super()._load_config(config)

        self._build_command = f'../bin/build.sh {self.cwd}'
        self._functional_test = f'../bin/run.py {self.cwd} test'
        self._security_test = f'../bin/run.py {self.cwd} pov'
        self._check_command = f'../bin/check.py --target {self.name}'

    @override
    def _functional_handler(self, stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        if returncode == 0 and b'KASAN' not in stdout:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Functional test failed (Message: At least one test case is failed)")

    @override
    def _security_handler(self, stdout, _stderr, returncode) -> Tuple[TestResult, str]:
        if returncode == 0 and b'KASAN' not in stdout:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Security test failed (Message: At least one bug can be triggered)")

class ArvoRunner(LegacyRunner):
    @override
    def _load_config(self, config: dict):
        self._build_commands = [ f'./run.py {config["id"]} build' ]
        self._functional_test = f'./run.py {config["id"]} sla'
        self._security_test = f'./run.py {config["id"]} pov'
        self._check_command = f'./check.py {self.name}'

    @property
    def cwd(self) -> Path:
        return self._root_dir.parent.parent

    def _cleanup(self):
        assert (self._root_dir / 'scripts').exists(), "scripts directory not found"
        # I need sudo to clean files/directories created by docker container
        subprocess.check_call([
            'sudo', 'git', 'clean', '-fdx'
        ], cwd=str(self._root_dir / 'src'), stdout=subprocess.DEVNULL)


class CPRunner(Runner):
    def __init__(self, cwd: Path, blob_file: Path, harness_name: str, sanitizers: Dict):
        super().__init__(cwd)
        self._build_command     = './run.sh build'
        self._functional_test   = './run.sh run_tests'
        self._security_test     = f'./run.sh run_pov {blob_file} {harness_name}'
        self._sanitizers     = sanitizers

    @property
    def sanitizers(self) -> Dict:
        return self._sanitizers

    @override
    def _get_result(self, name: str, stdout: bytes,
                    stderr: bytes, returncode: int) -> Tuple[bytes, bytes, int]:
        action = convert_to_aixcc_action(name)
        if action is None:
            # This is just a command, not predefined action
            return stdout, stderr, returncode

        result_dir = self._extract_result_dir(action)
        return self._read_result(result_dir)

    def _extract_result_dir(self, action: str) -> Path:
        output_dir = self.cwd / 'out' / 'output'
        results = sorted(list(output_dir.glob(f'*-{action}')), key=lambda x: x.name)
        return Path(results[-1])        # Most recent one

    def _read_result(self, result_dir: Path) -> Tuple[bytes, bytes, int]:
        try:
            returncode = int((result_dir / 'exitcode').read_text().strip())
            stdout = (result_dir / 'stdout.log').read_bytes()
            stderr = (result_dir / 'stderr.log').read_bytes()
        except (FileNotFoundError, ValueError):
            return b'', b'', -1
        return stdout, stderr, returncode

    def _build_handler(self, stdout: bytes,
                       stderr: bytes, returncode: int) -> Tuple[TestResult, str]:
        if returncode == 0:
            return (TestResult.OK, "")
        else:
            msg = stdout + b'\n' + stderr
            return (TestResult.FAILURE, f"Build failed (Message: {msg.decode('utf-8', 'ignore')})")

    def _functional_handler(self, stdout: bytes,
                            stderr: bytes, returncode: int) -> Tuple[TestResult, str]:
        if returncode == 0:
            return (TestResult.OK, "")
        else:
            return (TestResult.FAILURE,
                    "Functional test failed (Message: At least one test case is failed)")

    def _security_handler(
            self, stdout: bytes, stderr: bytes, returncode: int
        ) -> Tuple[TestResult, str]:
        if returncode != 0:
            return (TestResult.ERROR, 'Security test failed (Message: internal error)')

        for _sanitizer_id, sanitizer_str in self.sanitizers.items():
            if sanitizer_str.encode() in stdout or sanitizer_str.encode() in stderr:
                return (TestResult.FAILURE,
                        f"Security test failed (Message: {sanitizer_str} found)")

        return (TestResult.OK, "")

class CPLinuxRunner(CPRunner):
    @override
    def _build_handler(self, stdout: bytes,
                       stderr: bytes, returncode: int) -> Tuple[TestResult, str]:
        if returncode == 0:
            return (TestResult.OK, "")
        else:
            msg = stderr
            return (TestResult.FAILURE, f"Build failed (Message: {msg.decode('utf-8', 'ignore')})")

class CPJenkinsRunner(CPRunner):
    @override
    def _build_handler(self, stdout: bytes,
                       stderr: bytes, returncode: int) -> Tuple[TestResult, str]:
        res, msg = super()._build_handler(stdout, stderr, returncode)

        if res == TestResult.OK:
            return (res, msg)
        else:
            msg = ""
            try:
                msg_err = (stdout + b'\n' + stderr).decode('utf-8', 'ignore')
                msg_err_list = msg_err.split("\n")
                for i in msg_err_list:
                    if i.strip().startswith("[ERROR]"):
                        msg = msg + i + "\n"
            except Exception: # pylint: disable=broad-exception-caught
                msg = ""
            return (res, f"Build failed (Message: {msg})")

class CPUserlandRunner(CPRunner):
    pass
