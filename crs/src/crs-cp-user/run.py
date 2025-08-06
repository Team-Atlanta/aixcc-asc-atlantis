#!/usr/bin/env python3
import yaml
import sys
import argparse
import os
import subprocess
import logging
import coloredlogs
import glob
import asyncio
import json
import aiofiles
import aiofiles.os
import filelock
import contextlib

from datetime import datetime
from pathlib import Path
from git import Repo
from preprocessor.preprocessor import run_preprocessor
from harness_repo_matcher import use_include_to_match_repo


IN_DOCKER_CONTAINER = os.environ.get("IN_DOCKER_CONTAINER", False)
DOCKER_HOST = os.environ.get("DOCKER_HOST", None)
OUR_DOCKER_HOST = os.environ.get("OUR_DOCKER_HOST", None)
ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
CP_ROOT = ROOT / "cp_root"
CRS_SCRATCH = ROOT / "crs_scratch"
BUILD_DIR_NAME = os.environ.get("BUILDER_DIR_NAME", "crs-cp-user")

if IN_DOCKER_CONTAINER:
    CP_ROOT = Path(os.environ.get("AIXCC_CP_ROOT", "/cp_root"))
    CRS_SCRATCH = Path(os.environ.get("AIXCC_CRS_SCRATCH_SPACE", "/crs_scratch"))

LOCK_DIR = CRS_SCRATCH / BUILD_DIR_NAME / 'lock'
SYNC_DIR = CRS_SCRATCH / BUILD_DIR_NAME / 'sync'

def s2b(s):
    return s.lower() in ['true', '1', 't', 'y', 'yes']

DEBUG = s2b(os.environ.get("DEBUG", "False"))

# testlang
ENABLE_PREPROCESSOR = s2b(os.environ.get("ENABLE_PREPROCESSOR", "False"))
ENABLE_REVERSER = s2b(os.environ.get("ENABLE_REVERSER", "False"))

# LLM modules
ENABLE_COMMIT_ANALYZER = s2b(os.environ.get("ENABLE_COMMIT_ANALYZER", "True"))
ENABLE_SEEDSGEN = s2b(os.environ.get("ENABLE_SEEDSGEN", "True"))
ENABLE_CRS_AGI = s2b(os.environ.get("ENABLE_CRS_AGI", "True"))

# feature modules
ENABLE_INSTR_CACHE = s2b(os.environ.get("ENABLE_INSTR_CACHE", "True"))
ENABLE_CRASH_COLLECTOR = s2b(os.environ.get("ENABLE_CRASH_COLLECTOR", "True"))
ENABLE_SEEDS_DISTILLATION = s2b(os.environ.get("ENABLE_SEEDS_DISTILLATION", "True"))

# fuzzers
ENABLE_HYBRID = s2b(os.environ.get("ENABLE_HYBRID", "False"))
ENABLE_BUILTIN_LIBFUZZER = s2b(os.environ.get("ENABLE_BUILTIN_LIBFUZZER", "True"))
ENABLE_LIBAFL_LIBFUZZER = s2b(os.environ.get("ENABLE_LIBAFL_LIBFUZZER", "True"))
ENABLE_STATIC_CC = s2b(os.environ.get("ENABLE_STATIC_CC", "True"))
ENABLE_NIX_CC = s2b(os.environ.get("ENABLE_NIX_CC", "True"))
ENABLE_LEGACY_CC = s2b(os.environ.get("ENABLE_LEGACY_CC", "True"))
BUILD_USERSPACE_CP = s2b(os.environ.get('BUILD_USERSPACE_CP', "False"))

# consts
CRS_USER_NODE = int(os.environ.get("CRS_USER_NODE", 0))
CRS_USER_CNT = int(os.environ.get("CRS_USER_CNT", 1))
CRS_USER_NCPU = int(os.environ.get("CRS_USER_NCPU", os.cpu_count()))

coloredlogs.install(fmt='%(asctime)s %(levelname)s %(message)s')

async def heartbeat_info(stop_event, msg, interval=60):
    if not DEBUG: return
    while not stop_event.is_set():
        logging.info(f"[heartbeat] {msg}\n")
        await asyncio.sleep(interval)

async def event_wait(evt, timeout):
    # Suppress TimeoutError because we'll return False in case of timeout
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(evt.wait(), timeout)
    return evt.is_set()

def debug_info(msg):
    if DEBUG: logging.info(msg)

def debug_cmd(cmd, cwd = None):
    if not DEBUG: return b""
    try:
        cmd = list(map(str, cmd))
        res = subprocess.check_output(cmd, cwd = cwd, stdin = subprocess.DEVNULL,
                                                       stderr = subprocess.DEVNULL)
        logging.info(' '.join(cmd) + "\n" + res.decode("utf-8", errors="ignore"))
        return res
    except:
        logging.error("Fail to run: " + " ".join(cmd))
        return b""

def run_cmd(cmd, cwd = None, env = None):
    try:
        cmd = list(map(str, cmd))
        return subprocess.check_output(cmd, cwd = cwd, env = env, stdin = subprocess.DEVNULL,
                                                       stderr = subprocess.DEVNULL)
    except:
        logging.error("Fail to run: " + " ".join(cmd))
        return b""

async def async_run_cmd(cmd, cwd = None, env = None, disable_info=False):
    try:
        cmd = list(map(str, cmd))
        proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd = cwd,
                env = env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if not disable_info:
            debug_info("Result of running " +  " ".join(cmd))
            debug_info((out + err).decode("utf-8", errors="ignore"))
        return out + err
    except:
        logging.error("Fail to run: " + " ".join(cmd))
        return b"Fail 1337"

async def async_debug_cmd(cmd, cwd=None, env=None):
    try:
        cmd = list(map(str, cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def read_stream(stream, name):
            while True:
                line = await stream.readline()
                if line:
                    print(f'[{name}] {line.decode("utf-8").rstrip()}')
                    debug_info(f'[{name}] {line.decode("utf-8").rstrip()}')
                else:
                    break

        await asyncio.wait([
            read_stream(proc.stdout, "stdout"),
            read_stream(proc.stderr, "stderr")
        ])

        await proc.wait()

        return proc.returncode
    except Exception as e:
        logging.error("Fail to run: " + " ".join(cmd))
        logging.error(str(e))
        return -1


async def async_copy_file(fr, to):
    await async_run_cmd(["rsync", "-a", fr, to])

async def async_copy_dir (fr, to):
    await async_run_cmd(["rsync", "-a", str(fr)+"/.", str(to)])

def remove_file (path):
    run_cmd (["rm", "-rf", str(path)])

async def write_to_file(path, content, mode=None):
     async with aiofiles.open(path, "w") as f:
        await f.write(content)
        await f.flush()
        if mode:
            await async_run_cmd(["chmod", str(mode), path])

async def async_remove_file (path):
    await async_run_cmd (["rm", "-rf", str(path)])

def copy_file (fr, to):
    run_cmd (["rsync", "-a", str(fr), str(to)])

def copy_dir (fr, to):
    run_cmd (["rsync", "-a", str(fr)+"/.", str(to)])

def rename (fr, to):
    run_cmd (["mv", str(fr), str(to)])

async def async_unzip(src, dst):
    if not str(src).endswith(".zip"):
        logging.error(f"[Warnning] Invalid file extension: {src}")
    await async_run_cmd(["unzip", "-n", str(src), "-d", str(dst)])

# use this for lazy copying to crs_scratch
async def async_copy_to_crs_scratch(src, dest_name=None):
    if dest_name == None:
        dest_name = Path(src).name
    dest = CRS_SCRATCH / BUILD_DIR_NAME / dest_name
    if not dest.exists():
        await async_copy_dir(src, dest)
    return dest
    
class Config:
    def __init__ (self):
        self.target_harness = None
        self.build_cache = False
        self.modules = None
        self.debug = False
        self.ncpu = os.cpu_count()

    def load (self, fname):
        if not os.path.exists(fname): return
        with open(fname) as f: config = json.load(f)
        for key in vars(self):
            if key in config: setattr(self, key, config[key])
        self.ncpu = int(self.ncpu)


class Module:
    def __init__ (self, name):
        self.name = name

    def info(self, msg, prefix=None):
        if prefix: logging.info(f"[{prefix}][{self.name}] {msg}")
        else: logging.info(f"[{self.name}] {msg}")

    def dbg_info(self, msg, prefix=None):
        if not DEBUG: return
        if prefix: logging.info(f"[{prefix}][{self.name}] {msg}")
        else: logging.info(f"[{self.name}] {msg}")

    def error(self, msg, prefix=None):
        if prefix: logging.error(f"[{prefix}][{self.name}] {msg}")
        else: logging.error(f"[{self.name}] {msg}")

    def is_on(self):
        # if CONFIG.modules == None: return
        # return self.name in CONFIG.modules
        # implement configurable modules
        return True

    def check_on(self):
        if self.is_on(): self.info("ON")
        else: self.info("OFF")

    def prepare(self, runner): pass
    async def async_run(self, runner): pass


class Commit_Analyzer(Module):
    def __init__(self):
        super().__init__("Commit-analyzer")
        event_lock_file_name = LOCK_DIR / 'commit_analyzer_event.lock'
        self.event_lock = filelock.AsyncFileLock(event_lock_file_name)
        parse_lock_file_name = LOCK_DIR / 'commit_analyzer_parse.lock'
        self.parse_lock = filelock.AsyncFileLock(parse_lock_file_name)
        self.event = asyncio.Event()
        self.parse = asyncio.Event()

    def is_on(self):
        return ENABLE_COMMIT_ANALYZER

    async def parse_changes(self, runner):
        self.info("parse changes")
        if not self.is_on(): 
            self.parse.set()
            self.info("Skip..")
            return None

        root = runner.crs / "commit-analyzer"
        script = root / "parse_repo.py"
        target = runner.ro_project.base
        out = runner.build_dir / "changes.json"
        async with self.parse_lock:
            if out.is_file():
                self.dbg_info(f'parse_changes already found {out}')
            else:
                cmd = [root / ".venv/bin/python3", script]
                cmd += ["-t", target]
                cmd += ["-o", out]
                await async_run_cmd(cmd, cwd = root)

        self.parse.set()

        if out.exists():
            self.info(f"Successfully parse changes: {out}")
            return out
        else:
            self.error(f"fail to parse changes, {out} does not exists")
            return None

    async def async_run(self, runner):
        if not self.is_on(): 
            self.event.set()
            return self.info("Skip..")
        root = runner.crs / "commit-analyzer"
        script = root / "run.py"
        target = runner.ro_project.base
        out = runner.build_dir / "candidates.json"
        workdir = runner.build_dir / "commit-analyzer"
        await aiofiles.os.makedirs(str(workdir), exist_ok = True)
        cmd = [root / ".venv/bin/python3", script]
        cmd += ["-t", target]
        cmd += ["--output", out]
        cmd += ["-w", workdir]
        cmd += ["--max_worker", 16]

        if not await event_wait(self.parse, 60*10):        
            self.event.set()
            return

        self.info("Analyzing with LLM")
        try:
            async with self.event_lock:
                if out.is_file():
                    self.dbg_info(f'async_run already found {out}')
                else:
                    await async_run_cmd(cmd, cwd = root)
                self.event.set()
            if out.exists():
                self.info(f"Successfully analyze commits by using LLM: {out}")
                return out
            else:
                self.error(f"fail to analyze by using LLM, {out} does not exists")
                return None
        except Exception as e:
            self.error(f"Error running commit analyzer: {e}")
            self.event.set()
            return None


class SeedsGen(Module):
    def __init__(self):
        super().__init__("SeedsGen")
        self.base_name = "llm-seed-generator-c"
        self.event = asyncio.Event()

    def is_on(self):
        return ENABLE_SEEDSGEN

    async def distill_seeds(self, hrunner, dst_corpus_dir):
        # crash seeds distillation
        all_seeds = []
        for file in await aiofiles.os.listdir(dst_corpus_dir):
            file_path = os.path.join(dst_corpus_dir, file)
            if os.path.isfile(file_path): 
                all_seeds.append(file_path)

        jobs = list(map(hrunner.distill_seed, all_seeds))
        self.dbg_info("Start deleting crash seeds")
        await asyncio.gather(*jobs)

    async def async_run(self, hrunner, nblobs=5):
        if not self.is_on(): 
            self.event.set()
            return self.info("Skip..")
        
        self.dbg_info("Prologue, Start generating seeds")
        
        if DEBUG:
            heartbeat_event = asyncio.Event()
            info_task = asyncio.create_task(heartbeat_info(heartbeat_event, "SeedsGen is still running", 30))

        crs_path = hrunner.runner.crs
        module_path = crs_path / self.base_name
        repo_dir = hrunner.repo_dir
        out_dir = hrunner.runner.seeds_dir / hrunner.id
        commit_analyzer_output = hrunner.runner.build_dir / "candidates.json"

        self.info(f"Start generating seeds for {hrunner.name}")
        if not await event_wait(hrunner.runner.commit_analyzer.event, 60*20):
            self.error("Unfortunately, commit analyzer did not finish in time")
            self.event.set()
            return

        if not await aiofiles.os.path.exists(commit_analyzer_output):
            self.error(f"Commit analyzer output does not exist: {commit_analyzer_output}")
            self.event.set()
            return

        if not await aiofiles.os.path.exists(out_dir):
            await aiofiles.os.makedirs(out_dir)

        cmd = [
            f"{module_path}/.venv/bin/python3",
            "run.py",
            "--src_repo_path", repo_dir,
            "--test_harness", hrunner.src,
            "--commit_analyzer_output", commit_analyzer_output,
            "--nblobs", str(nblobs),
            "--output_dir", out_dir,
            "--workdir", module_path
        ]


        await async_run_cmd(cmd, cwd=module_path)
        
        out_nblobs = len(glob.glob(f"{out_dir}/*"))
        self.info(f"{out_nblobs} seeds are generated at {out_dir}")
        self.info(f"Start distilling seeds at {out_dir}")
        if ENABLE_SEEDS_DISTILLATION:
            await self.distill_seeds(hrunner, out_dir)

        if DEBUG: 
            heartbeat_event.set()
            await info_task
        self.event.set()


class CrashCollector(Module):
    '''
        workflow: new crash? -> run the verifier -> submit the VD
    '''
    def __init__(self, ident="", interval=30):
        super().__init__(f"CrashCollector ({ident})")
        self.crashes = set()
        self.sanitizer_keys = set()

        self.identifier = ident
        self.interval = interval
        self.files_state = {}

        self.lock = asyncio.Lock()

    def info(self, msg, prefix=None):
        if prefix: logging.info(f"[{prefix}][{self.name}] {msg}")
        else: logging.info(f"[{self.identifier}_Monitor] {msg}")

    def dbg_info(self, msg, prefix=None):
        if not DEBUG: return
        if prefix: logging.info(f"[{prefix}][{self.name}] {msg}")
        else: logging.info(f"[{self.identifier}_Monitor] {msg}")

    def is_on(self):
        return ENABLE_CRASH_COLLECTOR

    async def __scan_directory(self):
        current_state = {}
        black_list = [".lafl_lock", ".tmp", ".metadata"]
        try:
            for file_path in glob.glob(os.path.join(self.path, '*')):
                try:
                    if any(file_path.endswith(b) for b in black_list):
                        continue
                    file_mtime = os.path.getmtime(file_path)
                    current_state[file_path] = file_mtime
                except FileNotFoundError:
                    continue
        except Exception as e:
            self.error(f"Error scanning directory: {e}")
        # self.dbg_info(f"Current state: {current_state}")
        return current_state

    def __check_sanitizer(self, output):
        output = output.decode("utf-8", errors="ignore")
        for k, v in self.project.sanitizers.items():
            # self.info(f"-> Sanitizer {k}: {v}<-")
            if v in output:
                SUMMARY="SUMMARY:"
                if SUMMARY in output:
                    output_log = output[output.find(v):]
                    res = output_log[output_log.find(SUMMARY):].split("\n")[0]
                    self.dbg_info("\n\n Debug res of check sanitizers:\n\n\t" + res +"\n\n")
                    return res
                return v
        self.dbg_info("\n[-] Unintended bug discovered, not submitting\n")
        return None

    async def __collect_crashes(self, path):
        blist = [".lafl_lock", ".tmp", ".metadata"]
        if any(path.endswith(b) for b in blist): return

        # if path in self.crashes: return
        # self.crashes.add(path)

        # verify
        async with self.lock:
            pre_verify_res = await self.project.async_run_pov(self.hrunner.name, path)
            if b'Fail 1337' in pre_verify_res: 
                self.error("Maybe garbage testcase, retry with validate_pov")
                # validate pov is race-free but it uses custom heuristics
                pre_verify_res = await self.hrunner.validate_pov(path)
        
        # use the SUMMARY line as key to deduplicate
        sanitizer_key = self.__check_sanitizer(pre_verify_res)
        if sanitizer_key == None: 
            self.dbg_info(f"# Unintended # Removing {path}")
            await async_run_cmd (["rm", "-rf", str(path)], disable_info=True)
            return

        if DEBUG:
            await self.hrunner.verifier.create_backup_blob(self.hrunner, path)

        # submit
        identifier = os.path.basename(Path(self.path.parent.parent))
        if os.environ.get("VAPI_HOSTNAME", False):
            logging.info(f"[{identifier}] *{self.hrunner.name}* Found VAPI_HOSTNAME, Submitting to VAPI")
        else:
            logging.info(f"[{identifier}] *{self.hrunner.name}* Do fake submitting. Cannot find VAPI_HOSTNAME")

        await self.hrunner.verifier.submit_vd(
            self.hrunner, sanitizer_key, path, self.queue_path)
    
    async def __monitor_loop(self):
        self.dbg_info(f"_{self.hrunner.name}_ Start monitoring {self.path}")
        while True:
            try:
                current_state = await self.__scan_directory()
                
                added_files = [f for f in current_state if f not in self.files_state]
                modified_files = [f for f in current_state if f in self.files_state and current_state[f] != self.files_state[f]]

                for file in added_files + modified_files:
                    await self.__collect_crashes(file)

                self.files_state = current_state
            except Exception as e:
                self.error(f"({self.hrunner.name}) Error in monitor loop: {e}")

            await asyncio.sleep(self.interval)
            self.dbg_info(f"** heartbeat ** -> {self.hrunner.name}")


    async def async_run(self, hrunner, run_pov_project, monitor_dir, queue_path=None):
        if not self.is_on(): return self.info("Skip..")
        self.path = monitor_dir

        if not os.path.exists(self.path):
            os.makedirs(self.path)
        # else:
        #     await async_remove_file(self.path)
        #     os.makedirs(self.path, exist_ok=True)
    

        self.hrunner = hrunner
        self.project = run_pov_project
        self.info(f"{self.project.name}-{hrunner.name}: {self.path}")
        self.queue_path = queue_path
        self.identifier = os.path.basename(Path(self.path.parent.parent))

        # load exisiting crashes to avoid duplication
        file_paths = glob.glob(os.path.join(self.path, '**'), recursive=True)
        # self.crashes.update(file_paths)
        self.files_state = await self.__scan_directory()

        await self.__monitor_loop() 


async def patch_copy_dir(fr, to):
    cmd = [
        "rsync", "-a",
        "--exclude=*.lafl_lock",
        "--exclude=*.tmp",
        "--exclude=*.metadata",
        "--exclude=*-[0-9]*",
        str(fr) + "/.", str(to)
    ]
    await async_run_cmd(cmd)


class Verifier(Module):
    '''
    Verifier for the VDs
    '''
    def __init__(self):
        super().__init__("Verifier")
        self.submitted = {}
        self.precompile_event = asyncio.Event()
        self.precompile_lock = filelock.AsyncFileLock(LOCK_DIR / 'precompile.lock')

    async def create_backup_blob(self, hrunner, pov_path):
        backup_dir = hrunner.runner.build_dir / "backup_blobs"
        if not await aiofiles.os.path.exists(backup_dir):
            await aiofiles.os.makedirs(backup_dir)

        backup_pov_path = backup_dir / f"{hrunner.name}-{hrunner.runner.project.base_name}-{os.path.basename(pov_path)}"
        if not await aiofiles.os.path.exists(backup_pov_path):
            await async_copy_file(pov_path, backup_pov_path)
            return backup_pov_path

    # should be called by runner
    async def precompile(self, runner):
        verifier_py = runner.crs / "verifier" / "verifier.py"

        # Make sure VAPI service is running
        cmd = [
            str(ROOT / "verifier/.venv/bin/python3"),
            str(verifier_py),
            "precompile",
            f"--project={runner.project.name}",
        ]

        if await event_wait(runner.commit_analyzer.event, 60*10):
            commit_hints_file = runner.build_dir / "candidates.json"
            if await aiofiles.os.path.exists(commit_hints_file): 
                cmd.append(f"--commit-hints-file={commit_hints_file}")

        precompile_sync = SYNC_DIR / f'precompile_{runner.project.name}'
        async with self.precompile_lock:
            if not await aiofiles.os.path.exists(precompile_sync):
                if os.environ.get("VAPI_HOSTNAME", False):
                    await async_run_cmd(cmd)
                self.dbg_info(f'Precompile command: {" ".join(cmd)}')
                precompile_sync.touch()

        self.precompile_event.set()

        
    async def submit_vd(self, hrunner, sanitizer_key, pov_path, queue_path=None):
        await hrunner.runner.verifier.precompile_event.wait()
        
        submit_id = hrunner.submit_id
        if submit_id not in self.submitted: self.submitted[submit_id] = {}
        if sanitizer_key in self.submitted[submit_id]: 
            self.dbg_info(f"Duplicated submission (key: {sanitizer_key})")

            self.dbg_info(f"# Duplicated # Removing {pov_path}")
            await async_run_cmd (["rm", "-rf", str(pov_path)], disable_info=True)

            # clean crash folder
            # crash_dir = hrunner.runner.project.out / "crashes"
            # if await aiofiles.os.path.exists(crash_dir):
            #     self.dbg_info(f"Cleaning crash folder: {crash_dir}")
            #     files = glob.glob(os.path.join(crash_dir, '*'))
            #     for file in files:
            #         await async_run_cmd (["rm", "-rf", str(pov_path)], disable_info=True)
            return

        self.submitted[submit_id][sanitizer_key] = True
        self.info(f"->Submit VD<-, {hrunner.runner.project.name}, {hrunner.submit_id}, { os.path.basename(pov_path) }")
        self.info(sanitizer_key)

        verifier_py = hrunner.runner.crs / "verifier" / "verifier.py"

        # Make sure VAPI service is running
        cmd = [
            str(ROOT / "verifier/.venv/bin/python3"),
            str(verifier_py),
            "submit_vd",
            f"--project={hrunner.runner.project.name}",
            f"--harness={hrunner.submit_id}",
            f"--pov={pov_path}"
        ]

        commit_hints_file = hrunner.runner.build_dir / "candidates.json"
        if await aiofiles.os.path.exists(commit_hints_file): 
            cmd.append(f"--commit-hints-file={commit_hints_file}")

        # python3 verifier.py submit_vd --project=mock-cp --harness=id_1 --pov=../mock-cp/exemplar_only/cpv_1/blobs/sample_solve.bin
        if not DEBUG: await async_run_cmd(cmd)
        if DEBUG: await self.create_backup_blob(hrunner, pov_path)


        # per patching team request
        if queue_path is not None:
            try:
                dst_path = CRS_SCRATCH / "corpus" / str(hrunner.submit_id)
                if not await aiofiles.os.path.exists(dst_path):
                    await aiofiles.os.makedirs(dst_path)
                
                if await aiofiles.os.path.exists(queue_path):
                    await patch_copy_dir(queue_path, dst_path)
            except Exception as e:
                self.error(f"Error copying queue path: {e}")
                return

        self.dbg_info(cmd)
        self.dbg_info("Should be submitted")

    async def check_vd(self, hrunner, vd_uuid):
        verifier_py = hrunner.runner.crs / "verifier" / "verifier.py"

        # python3 verifier.py check_vd --vd-uuid=ca605d5e-69fa-4307-9bf4-846c50a2bf56
        # pending
        await async_run_cmd([ROOT / "verifier/.venv/bin/python3", verifier_py, "check_vd", f"--vd-uuid={vd_uuid}"])

class CRSAGI(Module):
    def __init__(self):
        super().__init__("CRSAGI")
        lock_file_name = LOCK_DIR / 'crs_agi.lock'
        self.lock = filelock.AsyncFileLock(lock_file_name)
        self.event = asyncio.Event()
    
    def is_on(self):
        return ENABLE_CRS_AGI

    async def async_get_dict(self, runner):
        if not self.is_on():
            self.event.set()
            return

        async with self.lock:
            self.info("Start getting dictionary")
            crs_agi_dir = runner.crs / "crs-agi"
            out_dir = runner.dict_dir

            if not await aiofiles.os.path.exists(out_dir):
                await aiofiles.os.makedirs(out_dir)

            for repo_dir in runner.project.src_repos:
                out_file = out_dir / f"{os.path.basename(repo_dir)}.dict"

                # Ignore previously generated from other machine
                if out_file.is_file():
                    self.dbg_info(f'Already found dictionary at {out_file} for {os.path.basename(repo_dir)}')
                else:
                    self.dbg_info(f"Start to generate dictionary for {os.path.basename(repo_dir)}")
                    cmd = [f".venv/bin/python3", f"src/fuzzdict.py", 
                        "--repo", str(repo_dir), 
                        "--out", out_file ]

                    self.dbg_info(f"[{os.path.basename(repo_dir)}]: {cmd}")
                    await async_run_cmd(cmd, cwd=crs_agi_dir)

                if DEBUG:
                    self.dbg_info(f"DEBUG READING {out_file}")
                    async with aiofiles.open(out_file, "r") as f:
                        content = await f.read()
                        self.dbg_info(f"Dictionary content:\n {content}")

                self.info(f"CRS-AGI finished to generate dictionary for {os.path.basename(repo_dir)}")

            self.event.set()


class Project_Analyzer(Module):
    def __init__(self):
        super().__init__("Project-Analyzer")
        self.project_names = None
        self.oss_dicts = None
        self.oss_corpus = None

        # lock_file_name = LOCK_DIR / 'project_analyzer.lock'
        # self.lock = filelock.AsyncFileLock(lock_file_name)
        # TODO For sharing, gotta serialize the data
        self.lock = asyncio.Lock()

        self.dicts_event = asyncio.Event()
        self.corpus_event = asyncio.Event()


    async def load_filenames(self, file_path):
        async with aiofiles.open(file_path, 'r') as file:
            return set(line.strip() for line in await file.readlines())
    
    async def generate_file_list(self, repo_dir):
        extensions = ('.h', '.hh', '.c', '.cc', '.hpp','.cpp')
        filenames = set()

        for root, _, files in os.walk(repo_dir):
            for file in files:
                if file.endswith(extensions):
                    filenames.add(os.path.basename(file))
        return filenames
    
    def jaccard_similarity(self, set1, set2):
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union)

    async def find_closest_project(self, runner, repo_dir):
        given_files = await self.generate_file_list(repo_dir)

        file_list_dir = runner.crs / 'project_analyzer' / 'file_list'
        max_similarity = 0
        closest_project = None
        
        for filename in os.listdir(file_list_dir):
            if filename.endswith('_filenames.list'):
                project_files = await self.load_filenames(file_list_dir / filename)
                similarity = self.jaccard_similarity(given_files, project_files)
                if similarity > max_similarity:
                    max_similarity = similarity
                    closest_project = filename.replace('_filenames.list', '')
        
        return closest_project, max_similarity

    async def match_all_repos(self, runner):
        if self.project_names is not None:
            return self.project_names

        closest_project, ratio = await self.find_closest_project(
                                        runner, runner.project.repo_dir)
        if ratio < 0.5:        
            # libcue: 0.76
            # openssl: 0.79
            self.project_names = []
            self.dbg_info(f"Closest project: {closest_project}, ratio: {ratio}")
            return self.project_names

        self.project_names = [closest_project] if closest_project else []

        self.dbg_info(f"Matched projects: {self.project_names}")
        self.dbg_info(f"Matched ratio: {ratio}")
        return self.project_names

    async def get_dict_paths(self, runner, project_name):
        dict_folder = runner.crs / "oss-fuzz-dict" / project_name
        if not await aiofiles.os.path.exists(dict_folder):
            return []

        dict_list_path = [
            os.path.abspath(os.path.join(dict_folder, item)) 
            for item in await aiofiles.os.listdir(dict_folder) 
            if await aiofiles.os.path.isfile(os.path.join(dict_folder, item))
        ]
        self.dbg_info(f"Found OSS Dicts for [{runner.project.name}]: {dict_list_path}")
        return dict_list_path

    async def get_corpus_path(self, runner, project_name):
        corpus_path = runner.crs / "fuzz_corpus" / project_name
        if await aiofiles.os.path.exists(corpus_path):
            self.dbg_info(f"Found OSS Corpus path for [{runner.project.name}]: {corpus_path}")

            zip_files = []
            dir_iter = await aiofiles.os.scandir(corpus_path)
            for entry in dir_iter:
                if entry.is_file() and entry.name.endswith('.zip'):
                    zip_files.append(Path(entry.path).resolve())

            return zip_files if zip_files else []

        return None

    async def get_oss_dicts(self, runner):
        '''
        Returns a list [path1, path2, ...] of OSS Dicts
        '''
        self.dbg_info("Start getting OSS Dicts")
        if self.oss_dicts:
            self.dicts_event.set()
            return self.oss_dicts

        project_names = await self.match_all_repos(runner)
        if not project_names:
            self.dicts_event.set()
            self.dbg_info("No project names found")
            return []

        res = await asyncio.gather(*[
            self.get_dict_paths(runner, project_name) 
            for project_name in project_names
        ])

        self.oss_dicts = list(set([item for sublist in res for item in sublist]))
        self.dbg_info(f"Found OSS Dicts: {self.oss_dicts}")
        self.dicts_event.set()
        return self.oss_dicts

    async def get_oss_corpus(self, runner):
        '''
        Returns a list [path1, path2, ...] of OSS Corpus
        '''
        self.dbg_info("Start getting OSS Corpus")
        if self.oss_corpus:
            self.corpus_event.set()
            return self.oss_corpus

        project_names = await self.match_all_repos(runner)
        if not project_names:
            self.corpus_event.set()
            self.dbg_info("No project names found")
            return []

        res = await asyncio.gather(*[
            self.get_corpus_path(runner, project_name)
            for project_name in project_names
        ])

        # Flatten the list of lists and remove None values
        flattened_res = [path for sublist in res if sublist for path in sublist]
        self.dbg_info(f"Found OSS Corpus: {flattened_res}")

        self.oss_corpus = list(set(flattened_res))
        self.corpus_event.set()
        return self.oss_corpus 


class CP:
    ''' Challenge Project'''
    def __init__(self, base):
        logging.info(f"[*] Loading CP from {base}")
        yaml_path = base / "project.yaml"
        with open(yaml_path, "r") as f:
            info = yaml.safe_load(f)

        self.base = base
        self.base_name = os.path.basename(base)
        self.out = base / "out"
        self.work = base / "work"

        self.name = info["cp_name"]
        self.lang = info["language"]
        self.sanitizers = info["sanitizers"]
        self.docker_image = info["docker_image"]

        cp_src = list(info["cp_sources"].keys())[0]
        # #deprecated: please use self.src_repos instead
        self.repo_dir = self.base / "src" / cp_src

        self.sources = {}
        for (name, cur) in info["cp_sources"].items():
            tmp = { 
                    "address": str(cur["address"]),
                    "ref": str(cur.get("ref", "")),
                    "artifacts": cur.get("artifacts", []),
                    "repo_dir": base / "src" / name,
            }
            self.sources[name] = tmp
        
        self.harnesses = {}
        for (name, cur) in info["harnesses"].items():
            tmp = { "name": str(cur["name"]),
                    "indocker_source": str('/'+cur["source"]),
                    "indocker_binary": str('/'+cur["binary"]),
                    "source": str(base / cur["source"]),
                    "binary": str(cur["binary"]),
                    "repo_dir": str(self.repo_dir)}
            self.harnesses[name] = tmp

        if len(self.harnesses) > 1:
            for (submit_id, harness) in self.harnesses.items():
                r = use_include_to_match_repo(harness["source"], self.src_repos)
                if r is not None:
                    harness["repo_dir"] = r
            
        lock_file_name = self.base / 'cp_run.lock'
        build_lock_file_name = self.base / 'cp_build.lock'
        # do not use this lock in CP itself to avoid deadlocks
        self.lock = filelock.AsyncFileLock(lock_file_name)
        # this lock should only be used by CP
        self.build_lock = filelock.AsyncFileLock(build_lock_file_name)

        # synchronous build_lock for init purposes
        init_build_lock = filelock.FileLock(build_lock_file_name)
        with init_build_lock:
            run_cmd(["git", "config", "--global", "--add", "safe.directory", self.base])
            for repo in self.src_repos:
                run_cmd(["git", "config", "--global", "--add", "safe.directory", repo])

        self.repo = None
        self.commits = None
        self.changes = None
        self.candidates = None
        self.has_docker_img = False

        self.build_cmd = "./run.sh -x build"

        with init_build_lock:
            self.__prepare_repo()


    def clone(self, dst: Path):
        # if not (CONFIG.build_cache and dst.exists()):
        if not dst.exists():
            logging.info(f"[*] Cloning {self.name} to {dst}")
            copy_dir(str(self.base), str(dst))

        return CP(dst)

    async def async_clone(self, dst: Path):
        # if not (CONFIG.build_cache and dst.exists()):
        if not dst.exists():
            logging.info(f"[*] Cloning {self.name} to {dst}")
            await async_copy_dir(str(self.base), str(dst))

        return CP(dst)

    def __prepare_repo(self):
        if BUILD_USERSPACE_CP and "oss-" not in self.base_name:
            logging.info("[+] Found BUILD_USERSPACE_CP, do make cpsrc-prepare")
            run_cmd(["make", "cpsrc-prepare"], cwd=self.base)
        else:
            try:
                self.repo = Repo(self.repo_dir)
                self.commits = list(map(lambda c: c.hexsha, self.repo.iter_commits()))
            except Exception as e:
                logging.info(f"[-] Error initializing the repo: {e}")

    def checkout(self, commit_idx):
        target_commit = self.commits[commit_idx]
        self.repo.git.checkout(target_commit, force=True)

    async def async_run_pov(self, harness_name, pov_path):
        async with self.lock:
            res = await async_run_cmd(
                ["./run.sh", "-x", "run_pov", pov_path, harness_name],
                cwd = self.base
            )
            return res

    def run_custom(self, cmd, env=None):
        return run_cmd(["./run.sh", "custom", cmd], cwd=self.base, env=env)

    async def async_run_custom(self, cmd, env=None):
        return await async_run_cmd(["./run.sh", "custom", cmd], cwd=self.base, env=env)

    def build_docker(self):
        logging.info("[Pre-game] Building CP docker image")
        run_cmd(["make", "docker-build"], cwd=self.base)
        run_cmd(["make", "docker-config-local"], cwd=self.base) 

    async def async_build_docker(self):
        logging.info("[Pre-game] Building CP docker image (async)")
        await async_run_cmd(["make", "docker-build"], cwd=self.base)
        await async_run_cmd(["make", "docker-config-local"], cwd=self.base)

    def __extract_timestamp(self, folder_name):
            try:
                timestamp_str = folder_name.split('--')[0]
                timestamp = datetime.fromtimestamp(float(timestamp_str))
                return timestamp
            except Exception as e:
                print(f"Error parsing timestamp from {folder_name}: {e}")
                return None

    async def transfer_dind_image(self):
        if not OUR_DOCKER_HOST or not DOCKER_HOST: return
        logging.info("[+] Found OUR_DOCKER_HOST, transferring CP image")

        # get base from path
        try:
            base_name = self.docker_image.split('/')[-1]
        except:
            base_name = self.docker_image

        # strip tag
        colon_idx = base_name.rfind(':')
        if colon_idx != -1:
            image_name = base_name[:colon_idx]
        else:
            image_name = base_name

        await aiofiles.os.makedirs(str(ROOT / 'assets'), exist_ok=True)
        logging.info(' '.join(['[CP]', f'DOCKER_HOST={DOCKER_HOST}', 'docker', 'save', '-o', f'{str(ROOT / "assets" / image_name)}.tar', self.docker_image]))
        await async_run_cmd(['docker', 'save', '-o', f'{str(ROOT / "assets" / image_name)}.tar', self.docker_image])

        os.environ['DOCKER_HOST'] = OUR_DOCKER_HOST
        logging.info(' '.join(['[CP]', f'DOCKER_HOST={OUR_DOCKER_HOST}', 'docker', 'load', '-i', f'{str(ROOT / "assets" / image_name)}.tar']))
        await async_run_cmd(['docker', 'load', '-i', f'{str(ROOT / "assets" / image_name)}.tar'])
            
    async def delete_logs(self):
        output_dir = self.out / "output"
        if output_dir.exists():
            await async_run_cmd(["rm", "-rf", str(output_dir)])


    def read_cmd_log(self, subcmd=''):
        '''
            supported subcmds: build, run_pov, run_tests, custom
        '''
        output_dir = self.out / "output"

        subfolders = glob.glob(str(output_dir / "*--*"))
        filtered_subfolders = [sf for sf in subfolders if f"--{subcmd}" in os.path.basename(sf)]

        if not filtered_subfolders:
            filtered_subfolders = subfolders

        sorted_subfolders = sorted(filtered_subfolders, key=lambda x: self.__extract_timestamp(os.path.basename(x)))
        if not sorted_subfolders:
            logging.info(f"No logs found")
            return {}

        latest_subfolder = sorted_subfolders[-1]
        def read_logs(folder):
            logs = {}
            try:
                with open(os.path.join(folder, 'docker.cid'), 'r') as f:
                    logs["docker_cid"] = f.read()
                with open(os.path.join(folder, 'stdout.log'), 'r') as f:
                    logs['stdout'] = f.read()
                with open(os.path.join(folder, 'stderr.log'), 'r') as f:
                    logs['stderr'] = f.read()
                with open(os.path.join(folder, 'exitcode'), 'r') as f:
                    logs['exit_code'] = f.read().strip()
            except Exception as e:
                logging.error(f"Error reading logs from {folder}: {e}")
            return logs

        logs = read_logs(latest_subfolder)
        if DEBUG:
            logging.info(f"[DOCKER-CP] Logs for '{subcmd}' at {os.path.basename(latest_subfolder)}:\n")
            for key, value in logs.items():
                logging.info(f"{key}: {value}")
            logging.info("-" * 40)
        return logs


    async def async_cmd_log(self, subcmd=''):
        '''
            NOTE: acquire the same lock for build and read_cmd_log
            supported subcmds: build, run_pov, run_tests, custom
        '''
        output_dir = self.out / "output"

        subfolders = glob.glob(str(output_dir / "*--*"))
        filtered_subfolders = [sf for sf in subfolders if f"--{subcmd}" in os.path.basename(sf)]
        if not filtered_subfolders:
            filtered_subfolders = subfolders

        sorted_subfolders = sorted(filtered_subfolders, key=lambda x: self.__extract_timestamp(os.path.basename(x)))
        if not sorted_subfolders:
            logging.info(f"No logs found")
            return {}

        latest_subfolder = sorted_subfolders[-1]
        async def read_logs(folder):
            logs = {}
            try:
                async with aiofiles.open(os.path.join(folder, 'docker.cid'), 'r') as f:
                    logs["docker_cid"] = await f.read()
                async with aiofiles.open(os.path.join(folder, 'stdout.log'), 'r') as f:
                    logs['stdout'] = await f.read()
                async with aiofiles.open(os.path.join(folder, 'stderr.log'), 'r') as f:
                    logs['stderr'] = await f.read()
                async with aiofiles.open(os.path.join(folder, 'exitcode'), 'r') as f:
                    logs['exit_code'] = await f.read()
                    logs["exit_code"] = logs["exit_code"].strip()
            except Exception as e:
                logging.error(f"Error reading logs from {folder}: {e}")
            return logs

        logs = await read_logs(latest_subfolder)
        if DEBUG:
            logging.info(f"[DOCKER-CP] Logs for '{subcmd}' at {os.path.basename(latest_subfolder)}:\n")
            for key, value in logs.items():
                logging.info(f"{key}: {value}")
            logging.info("-" * 40)
        return logs


    def build(self, custom_script=None, env=None, info=""):
        '''
            preapre, build, and instrument the target challenge
        '''

        if BUILD_USERSPACE_CP:
            logging.info("[+] Found BUILD_USERSPACE_CP, building CP Docker")
            self.build_docker()

        if info == "": info = self.name
        if custom_script:
            logging.info(f"[{self.name}] Custom Instrumentation with ./run.sh custom {custom_script}")
            run_cmd([custom_script], cwd=self.base, env=env)
        else:
            logging.info(f"[{info}] Raw CP building ./run.sh build")
            run_cmd(["./run.sh", "build"], cwd=self.base, env=env)
        if DEBUG: self.read_cmd_log("build")

    async def async_build(self, custom_script=None, env=None, info=""):
        '''
            preapre, build, and instrument the target challenge
        '''
        async with self.build_lock:
            if BUILD_USERSPACE_CP:
                logging.info("[+] Found BUILD_USERSPACE_CP, building CP Docker")
                await self.async_build_docker()

            if info == "": info = self.name
            if custom_script:
                logging.info(f"[{self.base_name}] Custom Instrumentation with ./run.sh custom {custom_script}")
                if DEBUG:
                    stop_event = asyncio.Event()
                    heartbeat = asyncio.create_task(heartbeat_info(
                        stop_event, 
                        f"[{self.base_name}] Custom Instrumentation with ./run.sh custom {custom_script}"
                    ))

                # trigger building
                await async_run_cmd([custom_script], cwd=self.base, env=env, disable_info=True)

                if DEBUG: 
                    stop_event.set()
                    await heartbeat
            else:
                logging.info(f"[{info}] Raw CP building ./run.sh build")
                await async_run_cmd(["./run.sh", "build"], cwd=self.base, env=env)
            if DEBUG: await self.async_cmd_log("build")

    def get_harnesses(self):
        return self.harnesses

    def get_sources(self):
        return self.sources

    @property
    def src_repos(self):
        srcs = self.get_sources()
        return [v['repo_dir'] for k, v in srcs.items()]

class Preprocessor(Module):
    '''
        Preprocessor finds C files to be analyzed by other modules (i.e. reverser)
        Depending on the results of this module,

        we can know the files can be analyzed by Harness Reverser and
        if we need to use harness gen to generate a fuzzing harness
    '''
    def __init__(self):
        super().__init__("Preprocessor")

    def is_on(self):
        return ENABLE_PREPROCESSOR

    async def async_run(self, hrunner):
        if not self.is_on(): return self.info("Skip..")
        preprocess_c = Path(hrunner.build_dir) / "preprocess.c"
        if not preprocess_c.is_file():
            # always store preprocessed file in workdir
            logging.info(f'[Preprocessor] preprocessing into {hrunner.build_dir}/')
            run_preprocessor(hrunner.src, hrunner.repo_dir, hrunner.build_dir, str(preprocess_c))


class HarnessReverser(Module):
    '''
        returns the grammar file based on the harness
    '''
    def __init__(self):
        super().__init__("HarnessReverser")

    def is_on(self):
        return ENABLE_REVERSER

    async def async_run(self, hrunner):
        if not self.is_on(): return self.info("Skip..")
        output_file = (Path(hrunner.build_dir) / "testlang").resolve()
        if not output_file.is_file():
            logging.info(f'[HarnessReverser] getting testlang')
            result = subprocess.run([ROOT / 'reverser/.venv/bin/python3',
                                     ROOT / 'reverser/run.py',
                                    '--workdir', Path(hrunner.build_dir).resolve(),
                                    '--target', str((Path(hrunner.build_dir) / "preprocess.c").resolve()),
                                    '--output', str(output_file),
                                    '--majority', '9',
                                    '--challenge', 'userspace'
                                    ])
        with open(output_file) as f:
            hrunner.testlang = f.read()
            logging.info(f'[HarnessReverser] reading from {output_file}')

class BuiltinLibfuzzer(Module):
    '''
        Since the CP itself has a built-in libfuzzer, we can use it as the last resort
    '''
    def __init__(self):
        super().__init__("Libfuzzer")
        self.lock = asyncio.Lock()
        self.crash_collector = CrashCollector(self.name)

    def is_on(self):
        return ENABLE_BUILTIN_LIBFUZZER
    
    async def build(self, hrunner):
        self.info("Building BuiltinLibfuzzer")
        async with self.lock:
            project = await hrunner.async_clone(self.name)
            # await project.async_build(info=self.name)

            self.info("[*] Dry-run dummy pov")
            await hrunner.runner.run_tests(project)
            await hrunner.run_dummy_pov(project)

    async def start_fuzzing(self, hrunner):
        project = await hrunner.async_clone(self.name)
        monitor_dir = project.out / "crashes"
        queue_dir = project.out / "corpus"
        os.makedirs(str(monitor_dir), exist_ok=True)

        self.info(f'({hrunner.name}) Starting CrashCollector at {monitor_dir}')

        monitor = asyncio.create_task(
            self.crash_collector.async_run(
                hrunner, hrunner.runner.project, monitor_dir, queue_dir))

        cpu_list = hrunner.ncpu[self.name]

        LAUNCHER_SCRIPT = "#!/bin/bash\n"
        LAUNCHER_SCRIPT += "cd /out\n"
        LAUNCHER_SCRIPT += f"./{hrunner.name} -artifact_prefix=/out/crashes/ "
        LAUNCHER_SCRIPT += f"-fork_corpus_groups=1 -ignore_crashes=1 "
        LAUNCHER_SCRIPT += f"-use_value_profile=1 "
        LAUNCHER_SCRIPT += f"-fork={len(cpu_list)} ./corpus\n"

        await write_to_file(project.out / "start_fuzz.sh", LAUNCHER_SCRIPT, 755)

        # prepare the seeds and corpus
        await hrunner.retrieve_seeds(project)

        self.info(f" ++{hrunner.name}++ BuiltinLibfuzzer is Running Now")
        await async_run_cmd(
            ["./run.sh", "custom", "/out/start_fuzz.sh"], cwd=project.base)
        
        await monitor
        self.error(f"BuiltinLibfuzzer is done ({hrunner.name})")


    async def async_run(self, hrunner):
        if not self.is_on(): return self.info("Skip..")
        if self.name not in hrunner.ncpu or len(hrunner.ncpu[self.name]) == 0:
            self.info("No CPUs allocated, skip..")
            return
        await self.build(hrunner)
        await self.start_fuzzing(hrunner)

class LibAFLHybrid(Module):
    '''
        The hybrid fuzzing workflow
    '''
    def __init__(self):
        super().__init__("Hybrid")
        self.lock = asyncio.Lock()

    async def async_run(self, hrunner):
        if not self.is_on(): return self.info("Skip..")

        if self.name not in hrunner.ncpu or len(hrunner.ncpu[self.name]) == 0:
            self.info("No CPUs allocated, skip..")
            return

class LibAFL_Libfuzzer(Module):
    def __init__(self):
        super().__init__("LibAFL_Libfuzzer")
        self.lock = asyncio.Lock()

        self.entry_bin_name = None
        self.fuzzer_subfolder_name = "libafl_libfuzzer"
        self.directory_dependencies = [
            self.fuzzer_subfolder_name,
            "third_party",
        ]
        self.rust_toolchain = [
            str(Path.home() / ".rustup"),
            str(Path.home() / ".cargo"),
        ]
        self.utils = [
            'build-libaflcc.sh',
        ]

        self.crash_collector = CrashCollector(self.name)
        self.cur_toolchain = 'dynamic'
        self.build_result = False
    
    def is_on(self):
        return ENABLE_LIBAFL_LIBFUZZER

    async def __copy_rust_toolchain(self, hrunner, project):
        '''
            copy rust toolchains, our fuzzer source codes
        '''
        self.dbg_info("Copying rust toolchains")
        cp_out = project.out
        crs_path = hrunner.runner.crs

        # Rust toolchain
        rust_dir = cp_out / 'rust'
        if not await aiofiles.os.path.exists(rust_dir):
            await aiofiles.os.makedirs(rust_dir)

        for dir_ in self.rust_toolchain:
            await async_copy_dir(crs_path / dir_, rust_dir / os.path.basename(dir_))

        # Subdirectories
        # FIXME use an offline installer? Slower but more reliable
        for dir_ in self.directory_dependencies:
            await async_copy_dir(crs_path / dir_, cp_out / dir_)

    async def __copy_dependencies(self, crs_path, project):
        '''
            copy shell scripts
            token files
        '''
        fuzzer_dir = crs_path / self.fuzzer_subfolder_name
        cp_out = project.out

        for util in self.utils:
            await async_copy_file(fuzzer_dir / util, cp_out / util)

        # build-cp.sh in cp-base
        await async_copy_file(fuzzer_dir / 'build-cp.sh', project.base / 'build-cp.sh')
        

    async def __copy_build_to_skytool(self, hrunner, project, toolchain_set, release_dir):
        '''
             copies build artificats to skytool
        '''
        self.dbg_info('copying build to skytool')

        crs_path = hrunner.runner.crs
        skynet32 = crs_path / 'libafl_libfuzzer/target/i686-unknown-linux-gnu/release/libskynet_libfuzzer.a'
        
        skytool_dir = project.out / "skytool"
        if not await aiofiles.os.path.exists(skytool_dir):
            await aiofiles.os.makedirs(skytool_dir)

        self.info(f"[*] copy to {skytool_dir}")
        for tool in toolchain_set:
            await async_copy_file(tool, skytool_dir / os.path.basename(str(tool)))
        await async_copy_file(skynet32, skytool_dir / 'libskynet_libfuzzer_32.a')

        # this one clang dependency
        libno_link_rt = list(release_dir.glob('build/libafl_cc-*/out/libno-link-rt.a'))
        if libno_link_rt:
            # just get one result
            libno_link_rt = libno_link_rt[0]
            # strip off release_dir
            parts = list(libno_link_rt.parts)
            dir_subparts = parts[-4:-1]
            # reconstruct skytool destination
            dir_path = skytool_dir / Path(*dir_subparts)
            if not await aiofiles.os.path.exists(dir_path):
                await aiofiles.os.makedirs(dir_path)
            libno_skytool = dir_path / parts[-1]
            await async_copy_file(libno_link_rt, libno_skytool)

        # create build wrapper here based on release_dir
        build_wrapper = f'''#!/usr/bin/env bash
HOST_RELEASE_PATH="{str(release_dir)}"
sudo mkdir -p "$HOST_RELEASE_PATH" || :
sudo chown $(id -u):$(id -g) "$HOST_RELEASE_PATH" || :
sudo ln -s "/out/skytool/build" "$HOST_RELEASE_PATH" || :
"$@"
'''
        async with aiofiles.open(project.out / 'build-wrapper.sh', 'w') as f:
            await f.write(build_wrapper)
            await f.flush()
        await async_run_cmd(["chmod", "755", project.out / 'build-wrapper.sh'])

    async def __copy_nix(self, hrunner, project):
        '''
            copy and check if the prebuilt (nix) libafl_cc is available
        '''
        crs_path = hrunner.runner.crs
        nix_path = crs_path / 'nix'

        # runtime deps
        scratch_nix_store = hrunner.runner.build_dir / 'nix/store'
        self.info(f'DEBUG: {scratch_nix_store}')
        scratch_nix_store.mkdir(parents=True, exist_ok=True)
        contents = ""
        async with aiofiles.open(nix_path / 'nix_runtimes.txt') as f:
            contents = await f.read()
        
        # for path in contents.splitlines():
        #     await async_copy_to_crs_scratch(path, path[1:])
        async_nix_store_copies = [async_copy_to_crs_scratch(Path(path), Path(path[1:])) for path in contents.splitlines()]
        await asyncio.gather(*async_nix_store_copies)

        release_dir = (
            hrunner.runner.crs /
            'libafl_libfuzzer_nix' /
            'target' /
            'release'
        )

        libafl_cc = release_dir / 'libafl_cc'
        libafl_cxx = release_dir / 'libafl_cxx'
        libskynet = release_dir / 'libskynet_libfuzzer.a'

        toolchain_set = [libafl_cc, libafl_cxx, libskynet]

        if not await aiofiles.os.path.exists(libafl_cc): return False

        await self.__copy_build_to_skytool(hrunner, project, toolchain_set, release_dir)

        self.info("[+] Using prebuilt nix libafl_cc")
        self.cur_toolchain = 'nix'
        return True

            
    async def __check_static_cc(self, hrunner, project):
        '''
            check if the prebuilt libafl_cc is available
        '''
        release_dir = (
            hrunner.runner.crs /
            self.fuzzer_subfolder_name /
            'target' /
            'x86_64-unknown-linux-gnu' /
            'release'
        )

        libafl_cc = release_dir / 'libafl_cc'
        libafl_cxx = release_dir / 'libafl_cxx'
        libskynet = release_dir / 'libskynet_libfuzzer.a'

        toolchain_set = [libafl_cc, libafl_cxx, libskynet]

        if not await aiofiles.os.path.exists(libafl_cc): return False

        # check if it is statically compiled
        output = await async_run_cmd(['ldd', libafl_cc])
        if 'statically linked' not in output.decode("utf-8", errors="ignore"): return False

        await self.__copy_build_to_skytool(hrunner, project, toolchain_set, release_dir)
        
        self.info("[+] Using prebuilt static libafl_cc")
        self.cur_toolchain = 'static'
        return True


    async def __build_libafl_cc(self, hrunner, project):
        '''
            Try statically-compiled  libafl_cc first
            If it does not work (e.g., missing dependencies), build it dynamically
        '''
        self.dbg_info("Processing libafl-cc")

        env = os.environ.copy()
        if DEBUG:
            # in debug env, we add --network none to make sure it works in competition
            extra_args = {}
            extra_args["DOCKER_EXTRA_ARGS"] = "--network none"
            env.update(extra_args)

        self.dbg_info("Building libafl-cc dynamically (slow...)")
        await self.__copy_rust_toolchain(hrunner, project)
        await project.async_run_custom('/out/build-libaflcc.sh', env=env)

        release_dir = (
            project.out /
            "libafl_libfuzzer" /
            'target' /
            'release'
        )

        libafl_cc = release_dir / 'libafl_cc'
        libafl_cxx = release_dir / 'libafl_cxx'
        libskynet = release_dir / 'libskynet_libfuzzer.a'
 
        while not await aiofiles.os.path.exists(libafl_cc):
            await asyncio.sleep(1)

        toolchain_set = [libafl_cc, libafl_cxx, libskynet]

        await self.__copy_build_to_skytool(hrunner, project, toolchain_set, release_dir)

    def __check_for_harness(self, hrunner, project):
        base_dir = project.base
        harness_bin = hrunner.bin
        result = (base_dir / harness_bin).is_file()
        self.dbg_info(f'Is {base_dir / harness_bin} a file? {result}')
        return result

    def __rm_harness(self, hrunner, project):
        base_dir = project.base
        harness_bin = hrunner.bin
        harness_path = (base_dir / harness_bin)
        if harness_path.is_file():
            harness_path.unlink()


    async def build(self, hrunner):
        self.info("LibAFL_Libfuzzer building")
        async with self.lock:
            # clone independent project
            project = await hrunner.async_clone(self.name)

            # for the html stuff
            await hrunner.runner.run_tests(project)
            await hrunner.run_dummy_pov(project)
            
            # copy utils, dict. corpus
            await self.__copy_dependencies(hrunner.runner.crs, project)

            # rm extra build harness for build checking to work properly
            self.build_result = False
            self.__rm_harness(hrunner, project)

            # try nix first due to static fuzzer slow performance
            if ENABLE_NIX_CC:
                self.dbg_info('trying nix')
                if (not self.build_result) and await self.__copy_nix(hrunner, project):
                    env = os.environ.copy()
                    extra_args = {}
                    extra_args["DOCKER_EXTRA_ARGS"] = f"-v {hrunner.runner.build_dir}/nix:/nix"
                    env.update(extra_args)
                    await project.async_build(custom_script='./build-cp.sh', env=env, info="LibAFL nix")
                    self.build_result = self.__check_for_harness(hrunner, project)
                    self.dbg_info(f'nix success: {self.build_result}')
            
            # we already have the static toolchains
            if ENABLE_STATIC_CC:
                if (not self.build_result) and await self.__check_static_cc(hrunner, project):
                    self.dbg_info('trying static')
                    # instrumentation
                    await project.async_build(custom_script='./build-cp.sh', info="LibAFL static")
                    self.build_result = self.__check_for_harness(hrunner, project)
                    self.dbg_info(f'static success: {self.build_result}')

            # processing instrumentation toolchain dynamic
            if ENABLE_LEGACY_CC:
                if not self.build_result:
                    await self.__build_libafl_cc(hrunner, project)
                    await project.async_build(custom_script='./build-cp.sh', info="LibAFL")
                    self.build_result = self.__check_for_harness(hrunner, project)
                    self.dbg_info(f'dynamic success: {self.build_result}')

    async def libfuzzer_fallback(self, hrunner, project, rebuild=False, corpus="./corpus"):
        self.info("**********************************************")
        self.info(f"* LibAFL fails for harness {hrunner.name} ***")
        self.info("!!!!!!!!!!! FALLBACK TO LIBFUZZER!!!!!!!!!!!!!")
        self.info("**********************************************")

        if DEBUG and BUILD_USERSPACE_CP: exit(0)

        if rebuild: await project.async_build(info=self.name)

        cpu_list = hrunner.ncpu[self.name]

        LAUNCHER_SCRIPT = "#!/bin/bash\n\n"
        LAUNCHER_SCRIPT += "cd /out\n\n"
        LAUNCHER_SCRIPT += f"./{hrunner.name} -artifact_prefix=/out/crashes/ "
        LAUNCHER_SCRIPT += f"-fork_corpus_groups=1 -ignore_crashes=1 "
        LAUNCHER_SCRIPT += f"-use_value_profile=1 "
        LAUNCHER_SCRIPT += "-create_missing_dirs=1 "
        LAUNCHER_SCRIPT += f"-fork={len(cpu_list)} "
        LAUNCHER_SCRIPT += f"{corpus} \n"

        await write_to_file(project.out / "start_fuzz.sh", LAUNCHER_SCRIPT, 755)

        self.info("Last Resort, Libfuzzer is Running Now")
        res = await async_run_cmd(["./run.sh", "custom", "/out/start_fuzz.sh"], cwd=project.base)

    async def async_run(self, hrunner):
        if not self.is_on(): return self.info("Skip..")
        if self.name not in hrunner.ncpu or len(hrunner.ncpu[self.name]) == 0:
            self.info("No CPUs allocated, skip..")
            return
        await self.build(hrunner)
        project = await hrunner.async_clone(self.name)
        monitor_dir = project.out / "crashes"
        queue_dir = project.out / "queue"

        self.info(f'({hrunner.name}) Starting CrashCollector at {monitor_dir}')

        monitor = asyncio.create_task(
            self.crash_collector.async_run(
                hrunner, hrunner.runner.project, monitor_dir, queue_dir))

        cpu_list = hrunner.ncpu[self.name]

        # build failed, directly fallback to libfuzzer
        if not self.build_result:
            await self.libfuzzer_fallback(hrunner, project, rebuild=True)
            await monitor
            return
        
        token_file = await hrunner.runner.retrieve_dicts(project)
        extra_args = ""        
        if token_file is not None: extra_args = f"-x ./{token_file}"
        
        # try to start LibAFL
        LAUNCHER_SCRIPT =  "#!/bin/bash\n\n"
        LAUNCHER_SCRIPT += "cd /out\n\n"
        LAUNCHER_SCRIPT += f"./{hrunner.name} --cores {','.join(map(str, cpu_list))} {extra_args}\n"
        await write_to_file(project.out / "start_fuzz.sh", LAUNCHER_SCRIPT, 755)
        
        # before fuzzing, setup the corpus and seeds
        await hrunner.retrieve_seeds(project)
        
        self.info(f"++{hrunner.name}++ LibAFL is Running Now !")
        res = await async_run_cmd(["./run.sh", "custom", "/out/start_fuzz.sh"], cwd=project.base)
        # start_fuzz should be an infinite loop
        if res: 
            # try to take the progress of LibAFL
            if await aiofiles.os.path.exists(queue_dir) and len(await aiofiles.os.listdir(queue_dir)):
                new_corpus = "./queue"
            else: 
                new_corpus = "./corpus"
            await self.libfuzzer_fallback(hrunner, project, rebuild=True, corpus=new_corpus)
        await monitor


class HarnessRunner:
    def __init__ (self, runner, idx, submit_id, **kwargs):
        self.submit_id = submit_id # the id in project.yaml
        self.id = f"harness_{idx}_node{CRS_USER_NODE}" # e.g., harness_0
        self.runner = runner
        
        self.name = kwargs["name"] # e.g., stdin_harness.sh, pov_harness
        self.indocker_bin = kwargs["indocker_binary"]
        self.bin = kwargs["binary"] # host path
        self.src = Path(str(kwargs["source"]))
        self.repo_dir = Path(str(kwargs["repo_dir"]))
        
        self.ncpu = None
        self.workdir = self.runner.workdir / self.id
        self.build_dir = self.runner.build_dir / self.id
        self.ncpu = {}
        self.disable = False
        
        # harness layer modules
        self.verifier = Verifier()
        self.seeds_gen = SeedsGen()
        self.builtin_libfuzzer = BuiltinLibfuzzer()
        self.libafl_libfuzzer = LibAFL_Libfuzzer()
        self.libafl_hybrid = LibAFLHybrid()

        os.makedirs(self.build_dir, exist_ok = True)
        os.makedirs(self.workdir, exist_ok = True)

        self.testlang = None
        self.lock = asyncio.Lock()

    def set_node_cpu_list(self, allocation):
        num_fuzzers = sum([1 if flag else 0 for flag in [
            ENABLE_BUILTIN_LIBFUZZER,
            ENABLE_LIBAFL_LIBFUZZER,
            ENABLE_HYBRID,
        ]])
        for machine, start, end in allocation:
            if machine != CRS_USER_NODE:
                continue
            # subtract num_fuzzers for CrashCollectors
            cpu_list = list(range(start, end + 1 - num_fuzzers))
            break
        else:
            cpu_list = []
        self.set_cpu_list(cpu_list)
        
    def set_cpu_list(self, cpu_list):
        # since our libafl_libfuzzer can specify specific CPU cores
        # e.g., [1,2,3,4,5,6,7,8]
        # so we need a list here
        # heuritic: 20% cpu for libfuzzer, and 80% cpu for libafl
        total_cpus = len(cpu_list)
        if total_cpus == 0:
            self.disable = True
        # TODO consider checking ENABLE_* flags, if useful at competition time
        n_builtin = total_cpus * 20 // 100
        n_libafl = total_cpus * 80 // 100
        
        # Calculate remainders
        remainder = total_cpus - n_builtin - n_libafl

        builtin_libfuzzer = self.builtin_libfuzzer
        libafl_libfuzzer = self.libafl_libfuzzer

        # Distribute remainders alternately
        i = 0
        while remainder > 0:
            if i % 2 == 0 and n_builtin < total_cpus:
                n_builtin += 1
            elif n_libafl < total_cpus:
                n_libafl += 1
            remainder -= 1
            i += 1

        # Assign CPUs
        self.ncpu[builtin_libfuzzer.name] = cpu_list[:n_builtin]
        self.ncpu[libafl_libfuzzer.name] = cpu_list[n_builtin:n_builtin+n_libafl]

    async def async_clone(self, module_name):
        '''
            make sure the project is cloned based on idx
        '''
        idx = f"{module_name}_{self.id}"
        if idx not in self.runner.fuzzing_projects:
            dst = self.runner.build_dir / idx
            self.runner.fuzzing_projects[idx] = self.runner.project.clone(dst)

        return self.runner.fuzzing_projects[idx]

    async def run_tests(self, project=None):
       await self.runner.run_tests(self, project) 

    async def run_pov(self, pov_path, project=None):
        project = project if project else self.runner.project
        cp_base_dir = project.base
        res = await async_run_cmd(
            ["./run.sh", "-x", "run_pov", pov_path, self.name],
            cwd = cp_base_dir
        )
        return res
    
    async def validate_pov(self, pov_path, project=None, copy_file=True):
        '''
        We cannot concurrently do ./run.sh run_pov as the race condition
        '''
        project = project if project else self.runner.project
        pov_validation = project.out / "pov_validation"
        dst_run_pov_path = project.out / "run_pov.sh"

        if not await aiofiles.os.path.exists(pov_validation):
            await aiofiles.os.makedirs(pov_validation, exist_ok=True)

        pov_name = os.path.basename(pov_path)
        if copy_file:
            pov_validation_path = pov_validation / pov_name
            await async_copy_file(pov_path, pov_validation_path)

        if not await aiofiles.os.path.exists(dst_run_pov_path):
            await async_copy_file(self.runner.crs / "run_pov.sh", dst_run_pov_path)

        return await async_run_cmd(
            ['./run.sh', 'custom', '/out/run_pov.sh', '-h', f'{self.name}', '-i', f'{pov_name}'],
            cwd=project.base
        )

    async def run_dummy_pov(self, project=None):
        project = project if project else self.runner.project
        cp_base_dir = project.base 
        out_dir = project.out

        async with project.lock:
            if not await aiofiles.os.path.exists(out_dir):
                project.build()

            pov_path = out_dir / "dummy_1337.blob"

            async with aiofiles.open(pov_path, "w") as f:
                await f.write("AAAAAAAAAA\r\n\r\n")
            
            while not await aiofiles.os.path.exists(pov_path):
                await asyncio.sleep(1)

            res = await async_run_cmd(
                ["./run.sh", "run_pov", pov_path, self.name],
                cwd = cp_base_dir
            )
            return res

    def check_sanitizer(self, output):
        output = output.decode("utf-8", errors="ignore")
        for k, v in self.runner.project.sanitizers.items():
            if v in output:
                SUMMARY="SUMMARY:"
                if SUMMARY in output:
                    output_log = output[output.find(v):]
                    res = output_log[output_log.find(SUMMARY):].split("\n")[0]
                    debug_info("\n\n Debug res of check sanitizers:\n\n\t" + res +"\n\n")
                    return res
                return v
        debug_info("\n[Hrunner.check] Unintended bug discovered, not submitting\n")
        return None

    async def distill_seed(self, seed_path):
        '''
            use run_pov and report crash seeds, then delete
        '''
        output = await self.validate_pov(seed_path)
        common_sanitizers = ["AddressSanitizer", "MemorySanitizer", "LeakSanitizer", "UndefinedBehaviorSanitizer"]
        if any(s in output.decode("utf-8", errors="ignore") for s in common_sanitizers):
            sanitizer_key = self.check_sanitizer(output)
            if sanitizer_key is None: 
                # Not intended, just remove?
                await async_remove_file(seed_path)
                return

            if DEBUG:
                await self.verifier.create_backup_blob(self, seed_path)

            # submit
            if os.environ.get("VAPI_HOSTNAME", False):
                logging.info("[Distill] Found VAPI_HOSTNAME, Submitting to VAPI")
                await self.verifier.submit_vd(self, sanitizer_key, seed_path)
            else:
                logging.info("[Distill] Do fake submitting. Cannot find VAPI_HOSTNAME") 
                await self.verifier.submit_vd(self, sanitizer_key, seed_path)
            
            # remove crashing seeds
            await async_remove_file(seed_path)

    async def retrieve_seeds(self, dst_project=None):
        project = dst_project if dst_project else self.runner.project
        harness_seeds_dir = self.runner.seeds_dir / self.id
        dst_corpus_dir = project.out / "corpus"

        logging.info(f"[{self.name}] Retrieving seeds")

        if await aiofiles.os.path.exists(dst_corpus_dir):
            await async_remove_file(dst_corpus_dir)

        await aiofiles.os.makedirs(dst_corpus_dir, exist_ok=True) 

        # oss
        debug_info(f"[{self.name}] Waiting OSS corpus")
        oss_corpus = await self.runner.retrieve_oss_corpus()
        if oss_corpus:
            logging.info(f"[{self.name}] Using OSS corpus: {oss_corpus}")
            for c in oss_corpus:
                await async_unzip(c, dst_corpus_dir)
        
        # llm seeds gen
        debug_info(f"[{self.name}] Waiting LLM generated corpus")

        await event_wait(self.seeds_gen.event, 60*15)

        if os.path.exists(harness_seeds_dir): 
            seeds = await aiofiles.os.listdir(harness_seeds_dir)
            if len(seeds): 
                logging.info(f"[{self.name}] Found {len(seeds)} seeds from {harness_seeds_dir}")
                await async_copy_dir(harness_seeds_dir, dst_corpus_dir)
            else:
                logging.info(f"[{self.name}] No seeds generated")

        # dummy
        logging.info(f"[{self.name}] creating dummy blob for safe manner")
        dummy_path = dst_corpus_dir / 'dummy_13371338'
        async with aiofiles.open(dummy_path, 'w') as f:
            await f.write('AAA\n1 2 3\n\nb\n')

        while not await aiofiles.os.path.exists(dummy_path):
            await asyncio.sleep(1)

        logging.info(f"[{self.name}] Seeds copied to {dst_corpus_dir}")

    async def infer_testlang(self):
        '''using harness_reverser to get the infered grammer of input'''
        await self.runner.preprocessor.async_run(self)
        await self.runner.reverser.async_run(self)

    async def run_builtin_libfuzzer(self):
        await self.builtin_libfuzzer.async_run(self)

    async def run_libafl_hybrid(self):
        await self.libafl_hybrid.async_run(self)

    async def run_libafl_libfuzzer(self):
        await self.libafl_libfuzzer.async_run(self)

    async def run_fuzzers(self):
        # make sure CPU allocation is ready
        logging.info(f"[{self.name}] Waiting for CPU allocation")
        await self.runner.cpu_alloc.wait()
        if self.disable:
            logging.info(f'[{self.id}] No CPU list, skip...')
            return

        for (n, c) in self.ncpu.items():
            logging.info(f'[{self.id}] {n} is allocated {c}')

        # event = asyncio.Event()
        # await event.wait()

        seeds_gen = asyncio.create_task(self.seeds_gen.async_run(self))
        libfuzzer = asyncio.create_task(self.run_builtin_libfuzzer())
        libafl_libfuzzer = asyncio.create_task(self.run_libafl_libfuzzer())
        libafl_hybrid = asyncio.create_task(self.run_libafl_hybrid())

        await seeds_gen
        await libfuzzer
        await libafl_hybrid
        await libafl_libfuzzer


class Runner:
    '''
        Fuzzer Runner
        @hanqing: ref runner: https://github.com/Team-Atlanta/CRS-cp-linux/blob/main/run.py#L539
    '''
    def __init__(self, project, build_dir = None, workdir = None):
        logging.info(f"[Runner] Using build directory: {build_dir}")
        logging.info(f"[Runner] Using work directory: {workdir}")

        self.project = project.clone(build_dir / f'{project.base_name}_{CRS_USER_NODE}')
        self.ro_project = project.clone(build_dir / f"ro-{project.base_name}_{CRS_USER_NODE}")

        self.workdir = workdir
        self.build_dir = build_dir

        # userspace crs
        self.crs = Path(os.path.abspath(os.path.dirname(__file__)))
        self.assets = self.crs / "assets"

        self.dict_dir = self.build_dir / "dicts"
        self.seeds_dir = self.build_dir / "seeds"

        remove_file(self.dict_dir)
        remove_file(self.seeds_dir)

        os.makedirs(self.assets, exist_ok=True)
        os.makedirs(self.dict_dir, exist_ok=True)
        os.makedirs(self.seeds_dir, exist_ok=True)

        # CP layer modules
        self.preprocessor = Preprocessor()
        self.reverser = HarnessReverser()
        self.commit_analyzer = Commit_Analyzer()
        self.crs_agi = CRSAGI()
        self.proj_analyzer = Project_Analyzer()
        self.verifier = Verifier() # only used for precompile

        self.modules = [
            self.preprocessor,
            self.reverser,
            self.commit_analyzer,
            self.crs_agi,
            self.proj_analyzer,
            self.verifier
        ]

        # we use independent project for each (harness, fuzzer) pair
        self.fuzzing_projects = {}

        self.cpu_alloc = asyncio.Event()
        logging.info(f"[+] Runner initialized for ***** {project.name} *****")

    async def run_tests(self, project=None):
        debug_info(f"[{self.project.name}] Running tests")
        project = project if project else self.project
        cp_base_dir = project.base 

        async with project.lock:
            res = await async_run_cmd(
                ["./run.sh", "run_tests"],
                cwd = cp_base_dir
            )
            return res

    async def run_dummy_pov_for_all(self, project=None):
        debug_info(f"[{self.project.name}] Running dummy pov")
        project = project if project else self.project
        cp_base_dir = project.base
        out_dir = project.out

        async with project.lock:
            if not await aiofiles.os.path.exists(out_dir):
                await project.async_build()

            pov_path = out_dir / "dummy_1337.blob"

            async with aiofiles.open(pov_path, "w") as f:
                await f.write("AAAAAAAAAA\r\n\r\n")

            res = b""
            for (_, harness) in self.project.get_harnesses().items():
                debug_info(f"[{self.project.name}] Running dummy pov for {harness['name']}")
                res += await async_run_cmd(
                    ["./run.sh", "run_pov", pov_path, harness["name"]],
                    cwd = cp_base_dir
                )
            return res

    async def bootstrap(self):
        logging.info("[*] Building and testing the original project for run_pov")
        await self.project.transfer_dind_image()
        await self.project.async_build()
        await self.run_dummy_pov_for_all()

        for m in self.modules:
            m.prepare(self)


    def find_machine(self, acc_list, idx):
        for i, m in enumerate(acc_list):
            if idx < m:
                return i - 1
        return len(acc_list) - 1

    async def allocate_tasks(self, machine_cpu_list, num_tasks):
        # total_cpus = num_machines * cpus_per_machine
        total_cpus = sum(machine_cpu_list)
        acc = 0
        cpu_acc_list = []
        for c in machine_cpu_list:
            cpu_acc_list.append(acc)
            acc += c
        base_allocation = total_cpus // num_tasks
        remaining_cpus = total_cpus % num_tasks

        allocations = []
        current_cpu = 0

        for task in range(num_tasks):
            allocation = []
            cpus_needed = base_allocation + (1 if remaining_cpus > 0 else 0)

            while cpus_needed > 0:
                machine = self.find_machine(cpu_acc_list, current_cpu)
                cpu_within_machine = current_cpu - cpu_acc_list[machine]
                end_cpu = min(cpu_within_machine + cpus_needed, machine_cpu_list[machine])
                allocation.append((machine, cpu_within_machine, end_cpu - 1))

                cpus_allocated = end_cpu - cpu_within_machine
                current_cpu += cpus_allocated
                cpus_needed -= cpus_allocated

            allocations.append(allocation)
            if remaining_cpus > 0:
                remaining_cpus -= 1

        return allocations

    async def alloc_node_cpu(self, harnesses):
        sync_lock_name = LOCK_DIR / 'sync.lock'
        sync_lock = filelock.AsyncFileLock(sync_lock_name)
        total_cpus = 0
        machine_cpu_map = {}
        async with sync_lock:
            await aiofiles.os.makedirs(SYNC_DIR, exist_ok=True)
            async with aiofiles.open(SYNC_DIR / f'cpus_{CRS_USER_NODE}', 'w') as f:
                await f.write(str(CRS_USER_NCPU))

        max_attempts = 100
        i = 0
        while i < max_attempts:
            for i in range(CRS_USER_CNT):
                async with sync_lock:
                    if not (SYNC_DIR / f'cpus_{i}').exists():
                        break
            else:
                break
            logging.info(f'[Alloc CPU]: waiting on other nodes to report CPU count')
            await asyncio.sleep(2)
            i += 1

        for i in range(CRS_USER_CNT):
            async with sync_lock:
                if (SYNC_DIR / f'cpus_{i}').exists():
                    async with aiofiles.open(SYNC_DIR / f'cpus_{i}') as f:
                        content = await f.read()
                        if content.isdigit():
                            machine_cpu_map[i] = int(content)
                            total_cpus += int(content)

        machine_cpu_list = []
        for i in range(CRS_USER_CNT):
            if i in machine_cpu_map:
                machine_cpu_list.append(machine_cpu_map[i])
            else:
                machine_cpu_list.append(0)
        logging.info(f'[Alloc CPU] Machine CPU list {machine_cpu_list}')
        
        allocations = await self.allocate_tasks(machine_cpu_list, len(harnesses))

        for i, h in enumerate(harnesses):
            h.set_node_cpu_list(allocations[i])

        self.cpu_alloc.set()

    
    async def alloc_cpu(self, harnesses, start_cpu_idx=0):
        # TODO: reserver CPUs for 
        # 1. crash collectors (can re-execute pov and keep scanning dirs)
        # 2. other LLM modules?
        
        # from env variable
        ncpu = int(CRS_USER_NCPU)
        logging.info(f'[Runner] found {ncpu} CPUs')
        ncpu -= (2 * len(harnesses)) # 2 fuzzers * n_harnesses = 2n_collectors
        cnt = len(harnesses)
        if cnt > 0:
            avg = int(ncpu / cnt)
            remainder = ncpu % cnt
        else:
            avg = ncpu
            remainder = 0

        # Initialize CPU index
        current_cpu_idx = start_cpu_idx

        for i, h in enumerate(harnesses):
            # Determine the number of CPUs for this harness
            if i < remainder:
                num_cpus = avg + 1
            else:
                num_cpus = avg
            
            # Generate the list of CPU indices
            cpu_list = list(range(current_cpu_idx, current_cpu_idx + num_cpus))
            h.set_cpu_list(cpu_list)
            
            # Update the current CPU index for the next harness
            current_cpu_idx += num_cpus

        self.cpu_alloc.set()

    async def retrieve_oss_corpus(self):
        if await event_wait(self.proj_analyzer.corpus_event, 60*3):
            return self.proj_analyzer.oss_corpus
        else:
            return []

    async def retrieve_oss_dicts(self):
        if await event_wait(self.proj_analyzer.dicts_event, 60*3):
            return self.proj_analyzer.oss_dicts
        else:
            return []

    async def retrieve_dicts(self, dst_project=None):
        project = dst_project if dst_project else self.project        
        logging.info(f"[{project.name}] Retrieving dictionaries")
        out_dict_path = project.out / f"{project.base_name}_concat.dict"

        # OSS
        oss_dicts = await self.retrieve_oss_dicts()
        if oss_dicts:
            logging.info(f"[{project.name}] Using OSS dictionaries: {oss_dicts}")
            for d in oss_dicts:
                await async_copy_file(d, self.dict_dir / os.path.basename(d))

        # LLM
        debug_info("[Dict Retrieve] Waiting for CRS AGI")
        
        await event_wait(self.crs_agi.event, 60*10)

        entries = await aiofiles.os.listdir(self.dict_dir)
        debug_info(entries)

        debug_info("[Dict Retrieve] Copying dictionaries")
        dict_contents = []
        for entry in entries:
            entry_path = os.path.join(self.dict_dir, entry)
            if await aiofiles.os.path.isfile(entry_path) and entry.endswith('.dict'):
                # Read the content of each dictionary file
                async with aiofiles.open(entry_path, 'r') as f:
                    content = await f.read()
                    dict_contents.append(content)
        
        if dict_contents == []:
            # fuzzer can work without dictionary
            dict_contents.append("AAA")

        # write into a single file in shared folder
        async with aiofiles.open(out_dict_path, 'w') as f:
            await f.write('\n'.join(dict_contents))

        logging.info(f"[Retrieve Dict] Dictionaries copied to {out_dict_path}")
        return f"{project.base_name}_concat.dict"

    async def async_fuzz_harness(self, hrunner):
        # TODO: probly a config file?
        if hrunner.name == "Mock CP":
            await hrunner.infer_testlang()

            # TODO: make sure testlang cannot be None
            # @hanqing: use asyncio.Event(), event.set(), and event.wait()
            if not hrunner.testlang:
                logging.error("Failed to infer the test language")
                return

        fuzzing = asyncio.create_task(hrunner.run_fuzzers())
        await fuzzing

    async def async_run(self):
        parse_changes = asyncio.create_task(self.commit_analyzer.parse_changes(self))
        commit_analyze = asyncio.create_task(self.commit_analyzer.async_run(self))
        get_oss_corpus = asyncio.create_task(self.proj_analyzer.get_oss_corpus(self))
        get_oss_dicts = asyncio.create_task(self.proj_analyzer.get_oss_dicts(self))
        crs_agi = asyncio.create_task(self.crs_agi.async_get_dict(self))
        verifier_precompile = asyncio.create_task(self.verifier.precompile(self))

        logging.info(f"[Runner] Starting hrunners")
        # event = asyncio.Event()
        # await event.wait()

        hrunners = []
        idx = 0
        for (submit_id, harness) in self.project.get_harnesses().items():
            logging.info(f"Found harness {submit_id}, name: {harness['name']}, harness_src: {harness['source']}")

            hrunner = HarnessRunner(self, idx, submit_id, **harness)
            hrunners.append(hrunner)
            idx += 1

        alloc_cpu = asyncio.create_task(self.alloc_node_cpu(hrunners))
        jobs = list(map(self.async_fuzz_harness, hrunners))
        await asyncio.gather(*jobs)
        await asyncio.gather(
            alloc_cpu, crs_agi, parse_changes, commit_analyze, 
            get_oss_corpus, get_oss_dicts, verifier_precompile)


def load_project(cp_root, cp_name, lang = ""):
    for fname in glob.glob(f"{cp_root}/**/project.yaml"):
        p = CP(Path(fname).parent)
        if p.name == cp_name and (lang == "" or p.lang == lang):
            return p
    return None

LLM_HOST_KEY = ["AIXCC_LITELLM_HOSTNAME", "LITELLM_URL"]
def sync_envs(keys):
    value = None
    for key in keys:
        value = os.environ.get(key)
        if value != None: break
    for key in keys:
        os.environ[key] = value

def setup_env():
    sync_envs(LLM_HOST_KEY)

def load_aixcc_cp(cp_root):
    # for each 4 hours, we only have one CP
    targets = ["nginx", "Mock CP"]
    for fname in glob.glob(f"{cp_root}/**/project.yaml"):
        p = CP(Path(fname).parent)
        # exclude linux kernel 
        if "linux kernel" in p.name: return None
        if "linux kernel" in p.name.lower(): return None
        # load nginx or mock cp for sure
        if p.name in targets: return p
        # load other C projects
        if p.lang == "C" or p.lang == "c": return p
    return None

def parse_args():
    parser = argparse.ArgumentParser(description="Skynet-user options parser")

    # the CP we're working on
    # TODO: modify to cp_root based instead of cp_name based
    parser.add_argument('--cp', type=str, default='aixcc_omni_cp', help='CP Name')
    return parser.parse_args()


def main(argv):
    args = parse_args()

    # TODO: introduce config in future
    # CONFIG.load("/crs-user.config")

    logging.info("[+] For CRS-user team members:")
    logging.info(" -- Please make sure there are no private keys/secrets are included")
    logging.info(" -- Please make sure the docker related commands are pre-game only")
    logging.info(" -- Reference workflow is in https://github.com/Team-Atlanta/CRS-cp-linux/blob/main/run.py")

    setup_env()

    os.makedirs(LOCK_DIR, exist_ok=True)
    
    cp_name = args.cp # e.g., "Mock CP", "nginx"
    debug_info(f"[+] Using cp_root: {CP_ROOT}")

    if cp_name == "aixcc_omni_cp":
        # load either nginx or mock cp
        target_cp = load_aixcc_cp(CP_ROOT)
    else:
        target_cp = load_project(CP_ROOT, cp_name)

    if target_cp == None:
        logging.info(f"[-] Failed to load CP `{cp_name}` in {CRS_SCRATCH}")
        exit(0)

    # TODO: potential usage of work_dir
    # currently I am using /out directory to handle everything
    #
    # We actually need to clone the project per instrumentation/harness?
    # e.g., a new cp docker for symcc
    # and another new cp docker for afl-clang-fast/
    #
    # However, when we want to kill the corresponding docker, we need extra logics
    #
    # another option:
    # after the instrumentation, we can copy the binary to another name but
    # it is hard to know if it has complex dependencies
    build_dir = CRS_SCRATCH / BUILD_DIR_NAME
    

    if not os.path.exists(build_dir):
        os.makedirs(build_dir, exist_ok=True)

    runner = Runner(project=target_cp, workdir=ROOT, build_dir=build_dir)
    asyncio.run(runner.bootstrap())
    asyncio.run(runner.async_run())


if __name__ == "__main__":
    exit_status = 0
    try:
        exit_status = main(sys.argv[1:])
    except Exception as e:
        logging.error(f"Fatal Error:\n {e}", file=sys.stderr)
        exit_status = 2
    exit(exit_status)
