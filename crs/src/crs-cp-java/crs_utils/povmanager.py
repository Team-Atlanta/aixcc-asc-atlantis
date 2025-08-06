import asyncio
import multiprocessing
from pathlib import Path
import random
import re
from time import sleep
from typing import Callable, List, Tuple
import hashlib

from .singleton import Singleton
from .utils import run_cmd, run_sh_lock
from .cp import CP
from .asynctask import AsyncTask


class ReportStatus:
    REFAIL = "regex_fail"
    ACCEPT = "accepted"
    DUPLICATED = "duplicated"
    RUN_POV_FAIL = "run_pov_fail"
    ALREADY_SOLVED = "already_solved"

class PoV:
    def __init__(self, harness_id, sanitizer_id, blob, cp_name):
        self.cp_name = cp_name
        self.harness_id = harness_id
        self.sanitizer_id = sanitizer_id
        self.blob: Path = blob
    
    def __str__(self):
        return f"PoV(harness_id: {self.harness_id}, sanitizer_id: {self.sanitizer_id}, blob_id: {self.blob})"
    
    def report_verifier(self, LOG, verifier: Path):
        cmd = [verifier]
        cmd += ["--harness", self.harness_id]
        cmd += ["--pov", self.blob]
        env = {"TARGET_CP": self.cp_name}
        verifier_proc = run_cmd(cmd, env=env, LOG=LOG)
        v_stdout = verifier_proc.stdout
        v_stderr = verifier_proc.stderr
        m = re.match(r"submit_id: (?P<submit_id>[^\s]+)", v_stdout.decode("utf-8"))
        if m:
            submit_id = m.group("submit_id").strip()
            if submit_id == "None":
                LOG.error(f"Failed to get submit_id; verifier stdout: {v_stdout}")
                LOG.error(f"Verifier stderr: {v_stderr}")
                return None
            return submit_id
        else:
            LOG.error(f"Failed to get submit_id; verifier stdout: {v_stdout}")
            LOG.error(f"Verifier stderr: {v_stderr}")
            return None
        

class PoVManager(AsyncTask, metaclass=Singleton):
    def __init__(self, crs: Path) -> None:
        self.verifier = crs / "verifier" / "verifier.py"
        # crs should be same for all PoVManager instances
        # {error_idx: (submit_id, harness_id, callback), ...}
        self.tasks: dict[str, Tuple[str, str, Callable]] = {}
        # {error_idx: [(PoV, callback), ...], ...}
        self.confirmed_povs: dict[str, list[Tuple[PoV, Callable]]] = {}
        self.confirmed_povs_lock = multiprocessing.Lock()
        # {error_idx: True, ...}
        self.solved: list[str] = [] #self.manager.list()
        # self.solved_lock = multiprocessing.Lock()
        self.LOG = self.logging_init("verifier")
        super().__init__()
    
    async def check(self):
        LOG = self.logging_init("verifier-check")
        interval = 30
        LOG.info("[Verifier] check started")
        while True:
            
            LOG.debug(f"[Verifier] {len(self.confirmed_povs)} tasks in the queue")
            with self.confirmed_povs_lock:
                for _, tasks in self.confirmed_povs.items():
                    if len(tasks) == 0:
                        continue
                    task = tasks[0]
                    pov, _ = task
                    LOG.debug(f"   - [Verifier] harness_id: {pov.harness_id}, tasks: {len(tasks)}")

            pending_remove = []
            with self.confirmed_povs_lock:
                for error_idx, tasks in self.confirmed_povs.items():
                    # Check if the sanitizer_id is already solved
                    is_solved = error_idx in self.solved

                    if is_solved:
                        if error_idx in self.confirmed_povs:
                            pending_remove.append(error_idx)
                        continue

                    if error_idx in self.tasks:
                        continue
                    
                    if len(tasks) == 0:
                        continue

                    # FIFO
                    task = tasks.pop(0)
                    pov, callback = task
                    submit_id = pov.report_verifier(LOG, self.verifier)
                    if submit_id is not None:
                        LOG.debug(f"[Verifier] PoV submitted with submit_id: {submit_id}")
                        self.tasks[error_idx] = (submit_id, pov.harness_id, callback)
                        self.confirmed_povs[error_idx] = tasks
                        if len(tasks) == 0:
                            pending_remove.append(error_idx)

                for error_idx in pending_remove:
                    tasks = self.confirmed_povs.pop(error_idx)
                    for _, callback in tasks:
                        callback()


            if len(self.tasks) == 0:
                await asyncio.sleep(interval)
                continue

            LOG.debug("[Verifier] pending tasks: " + print_tasks(self.tasks))
            proc = await asyncio.create_subprocess_exec(
                "python3", self.verifier, "--check",
                stdout = asyncio.subprocess.PIPE,
                stderr = asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode("utf-8").strip()
            stderr = stderr.decode("utf-8").strip()

            if len(stderr) != 0:
                LOG.debug("   - [Verifier] verifier stderr: " + stderr)

            povs = out.splitlines()
            tasks_remove = []
            for pov in povs:
                pov = pov.strip()
                if len(pov.split(":")) != 3:
                    LOG.error("   - [Verifier] invalid pov:" + pov)
                    continue
                pov_split = pov.split(":")
                reason, submit_id = pov_split[0], pov_split[1]
                for error_idx, task in self.tasks.items():
                    task_submit_id, harness_id, callback = task
                    if task_submit_id == submit_id:
                        if reason == "accepted":
                            LOG.debug("   - [Verifier] accepted pov:" + pov)
                            tasks_remove.append(error_idx)
                            callback()
                            self.solved.append(error_idx)
                            LOG.info(f"   - [Verifier] solved BIC: {len(self.solved)}")
                        elif reason == "rejected":
                            LOG.debug("   - [Verifier] rejected pov:" + pov)
                            tasks_remove.append(error_idx)
                        elif reason == "duplicated":
                            LOG.debug("   - [Verifier] duplicated pov:" + pov)
                            tasks_remove.append(error_idx)
                        else:
                            LOG.error("   - [Verifier] unknown pov:" + pov)

            for error_idx in tasks_remove:
                self.tasks.pop(error_idx)

            
            await asyncio.sleep(interval + random.uniform(-interval/2, interval/2))

    def check_with_run_sh(self, cp:CP, harness_id, blob_filename: str):
        harness_name:str = cp.get_harness(harness_id).name
        proc = cp.run_sh("run_pov " + blob_filename + " " + harness_name)
        output = proc.stdout + proc.stderr
        output = output.decode("utf-8").strip()

        add_error_lines = False
        error_lines = []
        report_error = False
        for line in output.splitlines():
            add_error_lines, error_lines, report_error = handle_line(line, add_error_lines, error_lines)
            if report_error:
                break
        
        error_logs = "\n".join(error_lines)

        sanitizer_id = cp.get_sanitizer_id(error_logs)
        if sanitizer_id is not None:
            sanitizer_msg = cp.get_sanitizer_msg(sanitizer_id)
            error_idx = refine_error_logs(error_lines, sanitizer_msg)
            return (sanitizer_id, error_idx)
        return None
    
    async def report(self, harness_id, blob_filename, cp: CP, callback: Callable):
        res = ReportStatus.RUN_POV_FAIL
        checked_pov = False
        with run_sh_lock:
            checked_pov = self.check_with_run_sh(cp, harness_id, blob_filename)

        if checked_pov != None:
            res = ReportStatus.REFAIL
            sanitizer_id, error_idx = checked_pov
            if error_idx in self.solved:
                return ReportStatus.ALREADY_SOLVED

            self.LOG.info(f"PoV confirmed with run_pov: {harness_id}, {sanitizer_id}, {blob_filename}")
            pov = PoV(harness_id, sanitizer_id, blob_filename, cp.name)

            with self.confirmed_povs_lock:
                self.confirmed_povs[error_idx] = self.confirmed_povs.get(error_idx, []) + [(pov, callback)]

            res = ReportStatus.ACCEPT

        return res

def refine_error_logs(error_lines: list[str], sanitizer_msg: str) -> str:  
    refined = []
    start = False
    for error_line in error_lines:
        error_line = error_line.strip()
        if error_line.startswith("== libFuzzer crashing input"):
            break
        if error_line.startswith("at "):
            start = True
        if start:
            refined.append(error_line)
        
    if len(refined) == 0:
        return hashlib.md5(error_lines[-1].encode()).hexdigest()
    else:
        error_logs = "\n".join(refined)
        error_logs = sanitizer_msg + "\n" + error_logs
        return hashlib.md5(error_logs.encode()).hexdigest()


def print_tasks(tasks: dict[str, Tuple[str, str, Callable]]):
    ret = []
    for error_logs, task in tasks.items():
        submit_id, harness_id, _callback = task
        ret.append(f"{harness_id}: {submit_id}")

    return "[" + ", ".join(ret) + "]"


    

def handle_line(line: str, add_error_lines: bool, error_lines: list[str]):
    report_error=False
    # line = line.strip()
    # Check stderr for Java exceptions
    if "Java Exception" in line:
        add_error_lines = True

    if add_error_lines:
        error_lines.append(line)

    if "Test unit written to" in line:
        # Report the crash
        report_error = True
        add_error_lines = False

    return add_error_lines, error_lines, report_error