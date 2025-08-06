#!/usr/bin/env python3

import os
import sys
import yaml
import glob
import argparse
import logging
import coloredlogs
import subprocess
from pathlib import Path
import asyncio
import random
import json
import time
from git import Repo
from threading import Thread
import hashlib
import time
import psutil

coloredlogs.install(fmt='%(asctime)s %(levelname)s %(message)s')

def BAR():
    logging.info("="*50)

def file_hash(fname):
    with open(str(fname), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()

def run_cmd(cmd, cwd = None):
    try:
        cmd = list(map(str, cmd))
        return subprocess.check_output(cmd, cwd = cwd, stdin = subprocess.DEVNULL,
                                                       stderr = subprocess.DEVNULL)
    except Exception as e:
        logging.error("Fail to run: " + " ".join(cmd))
        err = str(e)
        logging.error(err)
        return err.encode()

async def async_run_cmd(cmd, cwd = None, env = os.environ, only_out=False, timeout=None, only_retcode=False):
    try:
        cmd = list(map(str, cmd))
        if timeout: cmd = ["timeout", str(timeout)] + cmd
        proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd = cwd, env = env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            if proc.returncode == 124:
                logging.error("Timeout: " + " ".join(cmd))
            else:
                logging.error("Fail to run: " + " ".join(cmd))
            logging.info(f"Exit {proc.returncode}")
            logging.info(err.decode("utf-8", errors="ignore")[:0x1000])
        if CONFIG.debug:
            logging.info("Result of running " +  " ".join(cmd))
            logging.info(f"Exit {proc.returncode}")
            logging.info((out + err).decode("utf-8", errors="ignore"))
        if only_out: return out
        if only_retcode: return proc.returncode
        return out + err
    except Exception as e:
        logging.error("Fail to run: " + " ".join(cmd))
        logging.error(str(e))
        return b""

async def refresh_dir(path):
    await async_run_cmd(["rm", "-rf", path])
    await async_run_cmd(["mkdir", "-p", path])
    return path

async def async_copy_file(fr, to):
    await async_run_cmd(["rsync", "-a", fr, to])

async def async_copy(fr, to):
    if not fr.exists(): return
    if fr.is_dir(): await async_run_cmd(["rsync", "-a", str(fr) + "/.", to])
    else: await async_run_cmd(["rsync", "-a", fr, to])

def remove_file (path):
    run_cmd (["rm", "-rf", str(path)])

async def async_remove_file(path):
    await async_run_cmd(["rm", "-rf", str(path)])

def copy_file (fr, to):
    run_cmd (["rsync", "-a", str(fr), str(to)])

def copy_dir (fr, to):
    run_cmd (["rsync", "-a", str(fr)+"/.", str(to)])

def rename (fr, to):
    run_cmd (["mv", str(fr), str(to)])

NODE_TYPE = "CP_LINUX_CRS_TYPE"
NODE_CNT = "CP_LINUX_CRS_CNT"
MAIN_NODE = "MAIN" # "WORKER_1", "WORKER_2"

def get_env(key):
    value = os.environ.get(key)
    if value == None:
        logging.error(f"env[{key}] is None")
        sys.exit(-1)
    return value

def distribute(targets, N):
    size = len(targets)
    each = int(size / N)
    remain = targets[each * N:]
    ret = []
    for i in range(N):
        ret.append(targets[each * i: each * (i+1)] + remain)
    return ret

class SharedFile:
    def __init__(self, path):
        self.path = path

    def __metadata(self):
        path = self.path
        return path.parent / f".meta_{path.name}"

    def finalize(self):
        with open(self.__metadata(), "wb") as f: f.write(b"")
        return self

    def write(self, data):
        with open(self.path, "wb") as f: f.write(data)
        self.finalize()

    def wait(self):
        logging.info(f"Wait SharedFile: {self.path}")
        path = self.__metadata()
        while not path.exists():
            time.sleep(1)

    async def async_wait(self):
        logging.info(f"Wait SharedFile: {self.path}")
        path = self.__metadata()
        while not path.exists():
            await asyncio.sleep(1)

    def __str__(self): return self.path.__str__()

class Config:
    def __init__ (self):
        self.target_harness = None
        self.build_cache = True
        self.modules = None
        self.debug = False
        self.ncpu = os.cpu_count()
        self.n_llm_lock = 3
        self.llm_limit = 70

    def load (self, fname):
        if not os.path.exists(fname): return
        with open(fname) as f: config = json.load(f)
        for key in vars(self):
            if key in config: setattr(self, key, config[key])
        self.ncpu = int(self.ncpu)
        env_ncpu = os.cpu_count()
        if env_ncpu < self.ncpu: self.ncpu = env_ncpu
        self.n_llm_lock = int(self.n_llm_lock)
        self.llm_limit = int(self.llm_limit)

    def is_main(self):
        return get_env(NODE_TYPE) == MAIN_NODE

    def is_worker(self): return not self.is_main()

    def __save_conf(self, build_dir, idx, data):
        path = build_dir / f"WORKER_{idx}.config"
        SharedFile(path).write(bytes(json.dumps(data), "utf-8"))

    def distribute_job(self, proj, build_dir):
        logging.info("Distribute jobs")
        node_cnt = int(get_env(NODE_CNT))
        if node_cnt == 1: return
        harnesses = list(map(lambda x: x["name"], proj.get_harnesses().values()))
        jobs = distribute(harnesses, node_cnt)
        self.target_harness = jobs[0]
        for i in range(1, node_cnt):
            data = { "target_harness" : jobs[i] }
            self.__save_conf(build_dir, i, data)

    def load_job(self, build_dir):
        logging.info("Load job")
        conf = build_dir / f"{get_env(NODE_TYPE)}.config"
        SharedFile(conf).wait()
        self.load(conf)

CONFIG = Config()

class Module:
    def __init__ (self, name):
        self.name = name

    def info(self, msg, prefix=None):
        if prefix: logging.info(f"[{prefix}][{self.name}] {msg}")
        else: logging.info(f"[{self.name}] {msg}")

    def error(self, msg, prefix=None):
        if prefix: logging.error(f"[{prefix}][{self.name}] {msg}")
        else: logging.error(f"[{self.name}] {msg}")

    def is_on(self):
        if CONFIG.modules == None: return True
        return self.name in CONFIG.modules

    def check_on(self):
        if self.is_on(): self.info("ON")
        else: self.info("OFF")

    def prepare(self, runner): pass
    async def async_run(self, runner): pass

async def get_llm_spend(interval = 10, N=3, timeout=10):
    llm_url = os.environ.get("AIXCC_LITELLM_HOSTNAME")
    llm_key = os.environ.get("LITELLM_KEY")
    cmd = ["curl", f"{llm_url}/key/info?key={llm_key}", "-X", "GET"]
    cmd += ["-H", f"Authorization: Bearer {llm_key}"]
    for i in range(N):
        ret = await async_run_cmd(cmd, only_out=True, timeout=timeout)
        try:
            ret = json.loads(ret.decode("utf-8", errors="ignore"))
            return ret["info"]["spend"]
        except:
            await asyncio.sleep(interval)
    logging.info("Fail to get llm spend..")
    return 0

class LLM_Module(Module):
    def __init__(self, name, runner):
        super().__init__(name)
        self.runner = runner

    def llm_lock(self): return self.runner.llm_lock

    async def async_run_llm(self, cmd, cwd = None, timeout=None):
        async with self.llm_lock():
            spend = await self.runner.llm_total_spend()
            if spend < CONFIG.llm_limit:
                return await async_run_cmd(cmd, cwd=cwd, timeout=timeout)
            else: self.info (f"Out of LLM credit {spend}")

class Reverser (LLM_Module):
    def __init__(self, runner):
        super().__init__("Reverser", runner)
        with open(runner.crs / "fuzzer/reverser/answers/fallback.txt") as f:
            self.fallback = f.read()

    def is_fallback(self, out):
        with open(out) as f: return f.read() == self.fallback

    async def async_run(self, hrunner, N_TRY = 3, out = None):
        for i in range(N_TRY):
            out = await self.__async_run(hrunner, out)
            if out != None and not self.is_fallback(out):
                return out
        out = hrunner.workdir / "testlang"
        with open(out, "wb") as f: f.write(self.fallback)
        return out

    async def __async_run(self, hrunner, out = None):
        reverser = hrunner.runner.crs / "fuzzer" / "reverser"
        if out == None: out = hrunner.workdir / "testlang"
        if self.is_on():
            run = reverser / "run.py"
            cmd = [run, "--workdir", hrunner.workdir]
            cmd += ["--target", hrunner.src, "--output", out]
            self.info(f"Analyze..", hrunner.name)
            await self.async_run_llm(cmd, cwd = str(reverser))
            if out.exists():
                self.info(f"Successfully get testlang at {out}", hrunner.name)
                return out
            else:
                self.error(f"Fail to get testlang", hrunner.name)
        else:
            self.info("Skip running", hrunner.name)
            answer = reverser / "answers" / (hrunner.name + ".txt")
            if answer.exists():
                self.info(f"Use already existing answer at {answer}", hrunner.name)
                await async_copy_file(answer, out)
                return out
            else:
                self.info(f"Cannot find the existing answer at {answer}", hrunner.name)

class SyzReverser(Module):
    def __init__(self):
        super().__init__("Syz-Reverser")
        self.ready = False

    def prepare(self, runner):
        if not self.is_on(): return
        BAR()
        self.info("Prepare..")
        runner.prepare_skytracer()
        BAR()
        self.ready = True

    def get_syzkaller_dir(self, runner):
        return runner.crs / "fuzzer/syz-reverser"

    async def wait_ready(self):
        while self.ready == False:
            await asyncio.sleep(1)

    async def retry(self, hrunner):
        testlang = hrunner.workdir / "testlang-second"
        testlang = await hrunner.runner.reverser.async_run(hrunner, out = testlang)
        return await self.async_run(hrunner, True, testlang)

    async def async_run(self, hrunner, retry=False, testlang = None):
        out = hrunner.workdir / (hrunner.name + "-syzlang.txt")
        if not self.is_on():
            self.info("Skip..", hrunner.name)
            return out
        await self.wait_ready()
        syzkaller = self.get_syzkaller_dir(hrunner.runner)
        skytracer = hrunner.runner.crs/ "fuzzer/SkyTracer/skytracer.py"
        syz_reverser = syzkaller / "bin/syz-reverser"
        if testlang == None: testlang = hrunner.testlang
        workdir = hrunner.workdir / "syz-reverser"
        os.makedirs(str(workdir), exist_ok=True)
        cmd = [syz_reverser]
        cmd += ["-harness", hrunner.get_skytracer_harness()]
        cmd += ["-kernel", hrunner.runner.skytracer_kernel]
        cmd += ["-output", out]
        cmd += ["-syzkaller", syzkaller]
        cmd += ["-testlang", testlang]
        cmd += ["-tracer", skytracer]
        cmd += ["-work", workdir]
        cmd += ["-harness_id", hrunner.id]
        cmd += ["-trace_timeout", 60]
        self.info(f"Infer syzlang from {testlang}", hrunner.name)
        ret = await async_run_cmd(cmd, cwd=syzkaller, timeout=600, only_retcode=True)
        if ret == 7 and not retry:
            self.info("Retry..")
            await async_remove_file(out)
            return await self.retry(hrunner)
        if out.exists():
            self.info(f"Successfully infer syzlang", hrunner.name)
            return out
        else:
            self.error(f"Fail to infer syzlang", hrunner.name)
            return None

CONFIG_REPO = "/path/to/challenge/repo"
class CVE_Analyzer (Module):
    def __init__ (self):
        super().__init__("CVE-analyzer")
        self.ready = False

    def prepare(self, runner):
        if not self.is_on(): return
        BAR()
        self.info("Prepare..")
        runner.prepare_init_kernel()
        runner.prepare_latest_kernel()
        BAR()
        self.ready = True

    async def wait_ready(self):
        while self.ready == False:
            await asyncio.sleep(1)

    async def async_run_static(self, runner):
        if not self.is_on():
            self.info("Skip running", "Static")
            return (None, None)
        await self.wait_ready()
        self.info("Start", "Static")
        root = runner.crs / "CVE-analyzer"
        config = root / "config.ini"
        repo = runner.ro_project.repo_dir
        out = runner.workdir / "cve_commits.json"
        with open(config, "rt") as f: data = f.read()
        with open(config, "wt") as f:
            data = data.replace(CONFIG_REPO, str(repo))
            f.write(data)

        cmd = ["python3", "run_cve_analyzer.py"]
        ret = await async_run_cmd(cmd, cwd = str(root), timeout=300)
        self.info("End", "Static")
        try:
            ret_json = json.loads(ret.decode("utf-8", errors="ignore"))
            with open(out, "wb") as f: f.write(ret)
            return (out, ret_json)
        except: return (None, None)

    async def __async_run(self, runner, poc_dir):
        if not self.is_on():
            self.info("Skip running")
            return poc_dir
        await self.wait_ready()
        init = runner.init_kernel
        latest = runner.latest_kernel
        project = runner.ro_project

        static_task = asyncio.create_task(self.async_run_static(runner))

        cmd  = ["./dynamic.py"]
        cmd += ["--proj", str(project.yaml)]
        cmd += ["--outdir", str(poc_dir)]
        cmd += ["--latest-kernel", str(latest)]
        cmd += ["--ncpu", CONFIG.ncpu]
        if init: cmd += ["--init-kernel", str(init)]
        self.info("Start", "Dynamic")
        await async_run_cmd(cmd, cwd = str(runner.crs / "CVE-analyzer"), timeout=600)
        self.info("End", "Dynamic")
        if poc_dir.exists():
            pocs = " ".join(os.listdir(poc_dir))
            self.info(f"Find POCs: {pocs}", "Dynamic")
        else: self.error("Fail to find POCs", "Dynamic")

        (runner.cve_commits, cve_json) = await static_task

        return poc_dir

    async def async_run(self, runner):
        poc_dir = runner.get_workdir("poc")
        if CONFIG.is_main():
            poc_dir = await self.__async_run(runner, poc_dir)
            await runner.to_shared_file(poc_dir)
            return poc_dir
        if CONFIG.is_worker():
            return await runner.from_shared_file(poc_dir)

class Converter(Module):
    def __init__(self):
        super().__init__("Converter")
        self.prepared = False
        self.lock = asyncio.Lock()
        self.done = {}

    def prepare(self, runner, require=False):
        if self.prepared: return
        if not self.is_on() and not require: return
        BAR()
        self.info("Prepare..")
        runner.prepare_skytracer()
        runner.prepare_latest_kernel()
        BAR()
        self.prepared = True

    async def wait_ready(self):
        while self.prepared == False:
            await asyncio.sleep(1)

    async def trace(self, runner, bin_dir):
        await self.wait_ready()
        async with self.lock:
            trace_dir = Path(str(bin_dir) + "-trace")
            if trace_dir.exists():
                return trace_dir
            self.info(f"Trace {bin_dir}")
            workdir = runner.workdir / "trace"
            os.makedirs(workdir, exist_ok=True)
            os.makedirs(trace_dir, exist_ok=True)
            cmd = ["python3", "-m", "converter.prepare"]
            cmd += ["--bin-dir", bin_dir]
            cmd += ["--out-dir", trace_dir]
            cmd += ["--kernel", runner.skytracer_kernel]
            cmd += ["--work-dir", workdir]
            cmd += ["--cpus", CONFIG.ncpu]
            await async_run_cmd(cmd, cwd = str(runner.crs / "fuzzer"))
            return trace_dir

    async def __submit_povs(self, hrunner, pov_dir, submitted):
        for fname in os.listdir(str(pov_dir)):
            fname = pov_dir / fname
            if fname not in submitted and fname.stat().st_size > 0:
                ret = await hrunner.submit_pov(fname)
                if not ret: self.info(f"Fail to submit {fname}")
                else: submitted[fname] = ret

    async def submit_povs(self, hrunner, pov_dir):
        submitted = {}
        while not self.done[str(pov_dir)]:
            await asyncio.sleep(15)
            await self.__submit_povs(hrunner, pov_dir, submitted)
        await self.__submit_povs(hrunner, pov_dir, submitted)

    async def convert(self, hrunner, bin_dir, is_poc):
        target = "poc" if is_poc else "seed"
        self.info(f"Convert {target}s at {bin_dir}", hrunner.name)
        if not self.is_on() and is_poc:
            return self.info("Skip..", hrunner.name), None
        await self.wait_ready()
        skytracer_harness = hrunner.get_skytracer_harness()
        if skytracer_harness == None:
            return self.info(f"Cannot find skytracer harness", hrunner.name), None
        trace_dir = await self.trace(hrunner.runner, bin_dir)
        workdir = hrunner.workdir / f"convert-{target}-workdir"
        os.makedirs(workdir, exist_ok=True)
        out = hrunner.workdir / f"converted-{target}"
        tmp_seed = workdir / "tmp-seeds"
        os.makedirs(out, exist_ok=True)
        os.makedirs(tmp_seed, exist_ok=True)
        cmd = ["python3", "-m", "converter.run"]
        cmd += ["--poc-dir", bin_dir]
        cmd += ["--harness", skytracer_harness]
        cmd += ["--testlang", hrunner.testlang ]
        if is_poc: cmd += ["--kasan-kernel", hrunner.runner.latest_kernel]
        cmd += ["--no-kasan-kernel", hrunner.runner.skytracer_kernel]
        cmd += ["--work-dir", workdir]
        cmd += ["--out-dir", out]
        cmd += ["--out-seed-dir", tmp_seed ]
        cmd += ["--proj-def", hrunner.runner.ro_project.yaml]
        cmd += ["--cpus", "2"]
        if trace_dir is not None: cmd += ["--prep-dir", trace_dir]
        if is_poc:
            self.done[str(out)] = False
            t0 = asyncio.create_task(self.submit_povs(hrunner, out))
        await async_run_cmd(cmd, cwd = str(hrunner.runner.crs / "fuzzer"))
        if is_poc:
            self.done[str(out)] = True
            await t0
        results = " ".join(os.listdir(out))
        self.info(f"Converted {target}s: {results}", hrunner.name)
        return (out, tmp_seed)

SYZLANG_TYPES = ["syz_harness_type1", "syz_harness_type2"]
def get_syzlang_type(syzlang):
    if not syzlang.exists(): return None
    with open(syzlang, "rt") as f:
        data = f.read()
        for ty in SYZLANG_TYPES:
            if ty in data: return ty
    return None


FILTER_DENY = [
    "^fs/exec.c",
    "^kernel/fork.c",
    "^kernel/pid.c",
    "^lib/maple_tree.c",
    "^net/9p/",
    "^fs/9p/"
]

class Syzkaller(Module):
    def __init__(self):
        super().__init__("Syzkaller")
        self.lock = asyncio.Lock()
        self.root_dir = None
        self.src = None

    def prepare(self, runner):
        if not self.is_on(): return
        BAR()
        self.info("Prepare..")
        runner.prepare_syzkaller()
        self.root_dir = self.get_root_dir(runner)
        BAR()

    def get_root_dir(self, runner):
        return runner.crs / "fuzzer/syzkaller"

    def prepare_cov_filter(self, hrunner):
        files, funcs, targets = [], [], []
        changes = hrunner.runner.load_changes()
        if changes:
            for c in changes.values():
                for f in c["files"]: files.append("^" + f)
        cands = hrunner.runner.load_candidates()
        if cands and changes:
            done = {}
            for c in cands:
                commit = c[1]
                if commit not in changes: continue
                if commit in done: continue
                done[commit] = True
                for f in changes[commit]["funcs"]:
                    funcs.append(f"^{f}$")
                target = c[3]
                if target != "": targets.append(f"^{target}$")
        files = list(set(files))
        funcs = list(set(funcs))
        targets = list(set(targets))
        return { "files": files, "functions": funcs, "targets": targets }

    def prepare_yaml(self, hrunner):
        path = hrunner.workdir / "syzkaller-config.yaml"
        workdir = hrunner.get_workdir("syzkaller")
        ty = get_syzlang_type(hrunner.syzlang)
        if ty == None:
            self.error("Invalid syzlang.. cannot get syzlang type")
            return None
        submit_id = hrunner.submit_id
        harness = hrunner.runner.get_harness_bin(submit_id)
        config = {
            "linux": str(hrunner.runner.syzkaller_kernel),
            "harness": str(harness),
            "harness_id": str(submit_id),
            "verifier": str(hrunner.runner.verifier),
            "img": "9p",
            "syscall": [f"{ty}${hrunner.id}_*"],
            "syzlang": [str(hrunner.syzlang), str(hrunner.syzlang_const)],
            "vm_count": hrunner.ncpu[self.name],
            "core": 1,
            "procs": 1,
            "workdir": str(workdir),
            "sanitizers": hrunner.runner.ro_project.sanitizers,
            "polling_corpus": str(workdir / "polling_corpus.db"),
            "filter_deny": FILTER_DENY,
            "filter": self.prepare_cov_filter(hrunner)
        }
        with open(path, "wt") as f: f.write(yaml.dump(config))
        return path

    async def build(self, hrunner):
        if not self.is_on(): return self.info("Skip..")
        yaml_path = self.prepare_yaml(hrunner)
        if not yaml_path: return
        self.info("Wait lock..", hrunner.name)
        async with self.lock:
            self.info("Build", hrunner.name)
            cmd = ["./scripts/run.py", str(yaml_path), "--build"]
            await async_run_cmd(cmd, cwd = self.root_dir)
            cmd = ["./scripts/run.py", str(yaml_path), "--clear"]
            await async_run_cmd(cmd, cwd = self.root_dir)
        self.yaml_path = yaml_path
        return (hrunner.get_workdir("syzkaller") / "bin/syz-manager").exists()

    async def async_run(self, hrunner):
        if not self.is_on(): return self.info("Skip..")
        self.info(f"Run with {hrunner.ncpu[self.name]} cores", hrunner.name)
        cmd = ["./scripts/run.py", str(self.yaml_path)]
        await async_run_cmd(cmd, cwd = self.root_dir)

class Commit_Analyzer(Module):
    def __init__(self):
        super().__init__("Commit-analyzer")
        self.done = False

    async def wait(self):
        while self.done == False:
            await asyncio.sleep(1)

    async def parse_changes(self, runner):
        self.info("parse changes")
        root = runner.crs / "commit-analyzer"
        script = root / "parse_repo.py"
        target = runner.ro_project.base
        out = runner.workdir / "changes.json"
        cmd = ["python3", script]
        cmd += ["-t", target]
        cmd += ["-o", out]
        await async_run_cmd(cmd, cwd = root, timeout=300)
        if out.exists():
            self.info(f"Successfully parse changes: {out}")
            return out
        else:
            self.error(f"fail to parse changes, {out} does not exists")
            return None

    async def __async_run(self, runner, out):
        if not self.is_on():
            self.info("Skip.. Use previous result")
            await async_copy(runner.crs / "llm-result/candidates.json", out)
            return out
        self.info("Analyze by using LLM")
        root = runner.crs / "commit-analyzer"
        script = root / "run.py"
        target = runner.ro_project.base
        workdir = runner.workdir / "commit-analyzer"
        os.makedirs(str(workdir), exist_ok = True)
        cmd = ["python3", script]
        cmd += ["-t", target]
        cmd += ["--output", out]
        cmd += ["-w", workdir]
        cmd += ["--max_worker", 5]
        await async_run_cmd(cmd, cwd = root, timeout = 900)
        if out.exists():
            self.info(f"Successfully analyze commits by using LLM: {out}")
            return out
        else:
            self.error(f"fail to analyze by using LLM, {out} does not exists")
            return None

    async def async_run(self, runner):
        out = runner.workdir / "candidates.json"
        if CONFIG.is_main():
            ret = await self.__async_run(runner, out)
            await runner.to_shared_file(out)
            return ret
        if CONFIG.is_worker():
            return await runner.from_shared_file(out)

class Seed_Selector(Module):
    def __init__(self):
        super().__init__("Seed-selector")

    def prepare(self, runner):
        if not self.is_on(): return
        return runner.converter.prepare(runner, True)

    async def async_run(self, runner):
        seed_dir = runner.workdir / "seeds"
        if not self.is_on():
            self.info("Skip..")
            return seed_dir
        self.info("Start")
        root = runner.crs / "fuzzer/seed-selector"
        script = root / "seed-selector.py"
        outdir = root / "assets"
        cmd = ["python3", script]
        cmd += ["--outdir", outdir]
        cmd += ["--changes", runner.changes]
        cmd += ["--no-want-c-files"]
        await async_run_cmd(cmd, cwd = root, timeout=300)
        out = outdir / "output.txt"
        bins = outdir / "bin"

        os.makedirs(str(seed_dir), exist_ok = True)

        with open(str(out), "rt") as f:
            for line in f.read().split("\n"):
                if line == "": continue
                bin = bins / line
                if bin.exists():
                    self.info(f"Found seed {line}")
                    rename(bin, seed_dir / line)
        return seed_dir

class SkyQEMU(Module):
    def __init__(self):
        super().__init__("SkyQEMU")

    def prepare(self, runner):
        if not self.is_on(): return
        return runner.converter.prepare(runner, True)

    async def sync_seed(self, hrunner, sleep=120):
        while True:
            if hrunner.built_syzkaller == False: return
            await asyncio.sleep(sleep)
            self.info("Sync seeds", hrunner.name)
            await hrunner.hybrid_sync_seeds(hrunner.blob_dir)

    async def async_run(self, hrunner):
        if not self.is_on(): return self.info("Skip..")
        self.info(f"Run with {hrunner.ncpu[self.name]} cores", hrunner.name)
        script = hrunner.runner.crs / "fuzzer/SkyQEMU/bin/run.py"
        workdir = hrunner.get_workdir("skyqemu")
        cmd = [script]
        cmd += ["--kernel", hrunner.runner.skytracer_kernel]
        cmd += ["--kasan-kernel", hrunner.runner.latest_kernel]
        cmd += ["--proj", hrunner.runner.ro_project.yaml]
        cmd += ["--target", hrunner.get_skytracer_harness() ]
        cmd += ["--harness-id", hrunner.submit_id]
        cmd += ["--ncpu", hrunner.ncpu[self.name]]
        cmd += ["--seed-dir", hrunner.blob_dir]
        cmd += ["--workdir", workdir]
        t = asyncio.create_task(self.sync_seed(hrunner))
        self.info(await async_run_cmd(cmd))
        await t

MAX_PRIORITY = 1000000
class Seed_Generator(LLM_Module):
    def __init__(self, runner):
        super().__init__("Seed-generator", runner)

    async def async_run(self, hrunner, nblobs=5):
        if not self.is_on(): return self.info("Skip..")
        runner = hrunner.runner
        workdir = hrunner.get_workdir("seed-gen")
        output_dir = await refresh_dir(workdir / "output-seeds")
        cwd = runner.crs / "fuzzer/llm-seed-generator/"
        cmd = ["python3", cwd / "run.py"]
        cmd += ["--src_repo_path", runner.ro_project.repo_dir]
        cmd += ["--testlang", hrunner.testlang]
        cmd += ["--test_harness", hrunner.src]
        cmd += ["--commit_analyzer_output", runner.candidates]
        cmd += ["--nblobs", nblobs]
        cmd += ["--output_dir", output_dir]
        cmd += ["--workdir", workdir]
        self.info(f"Generate seeds by using LLM (nblobs = {nblobs})")
        await self.async_run_llm(cmd, cwd = cwd)
        await hrunner.to_blob_dir(output_dir, MAX_PRIORITY)

class Project:
    def __init__ (self, base: Path, read_only=True):
        yaml_path = base / "project.yaml"
        with open(yaml_path, "r") as f:
            info = yaml.safe_load(f)
        self.raw_info = info
        self.yaml = yaml_path
        self.base = base
        self.name = info["cp_name"]
        self.lang = info["language"]
        self.sanitizers = info["sanitizers"]
        self.harnesses = {}
        for (submit_id, cur) in info["harnesses"].items():
            tmp = { "source": str(base / cur["source"]),
                    "binary": str(base / cur["binary"]),
                    "name": cur["name"] }
            self.harnesses[submit_id] = tmp
        cp_src = list(info["cp_sources"].keys())[0]
        self.repo_dir = self.base / "src" / cp_src
        for target in [self.repo_dir, self.base]:
            run_cmd (["git", "config", "--global", "--add", "safe.directory", target])
        self.repo = Repo(str(self.repo_dir))
        self.commits = list(map(lambda c: c.hexsha, self.repo.iter_commits()))
        # Result from commit analyzer
        self.changes = None
        self.candidates = None

        self.has_docker_img = False

    def clone(self, dst: Path):
        if not (CONFIG.build_cache and dst.exists()):
            logging.info(f"Copy project into {dst}")
            copy_dir(self.base, dst)
        return Project(dst, False)

    def checkout(self, commit_idx):
        target_commit = self.commits[commit_idx]
        self.repo.git.checkout(target_commit, force=True)

    def __build(self):
        logging.info(f"Compile {self.name} at {self.base}")
        run_cmd(["./run.sh", "build"], cwd = self.base)

    def build(self, commit_idx, out_base, checkout=True, copy_vmlinux=False):
        if (out_base / "arch/x86/boot/bzImage").exists(): return out_base

        logging.info(f"Build kernel with commit_idx: {commit_idx} and save into {out_base}")
        img = self.repo_dir / "arch/x86/boot/bzImage"
        remove_file(img)
        if checkout: self.checkout(commit_idx)
        self.__build()
        if img.exists():
            logging.info("Successfully build kernel")
            if str(self.repo_dir) != str(out_base):
                os.makedirs(str(out_base / "arch/x86/boot"), exist_ok = True)
                copy_file(img, out_base / "arch/x86/boot/bzImage")
                if copy_vmlinux:
                    copy_file(self.repo_dir / "vmlinux", out_base / "vmlinux")
            return out_base
        logging.error("Fail to build kernel")
        return None

    def get_harnesses(self):
        if CONFIG.target_harness:
            ret = {}
            for (submit_id, harness) in self.harnesses.items():
                name = harness["name"]
                if name in CONFIG.target_harness:
                    ret[submit_id] = harness
            return ret
        return self.harnesses

class Syzlang_Generator(LLM_Module):
    def __init__(self, runner):
        super().__init__("Syzlang-generator", runner)
        self.runner = runner

    async def use_answer(self, driver_path, out):
        answers = self.runner.crs / "fuzzer/syzlang-gen/answers"
        ans = answers / out.name
        if ans.exists():
            await async_copy_file(ans, out)
            return self.info(f"Use {ans}")
        return self.info("Skip..")

    async def async_run(self, driver_path, output_dir):
        out = output_dir / f"{driver_path.name}-syzlang.txt"
        if not self.is_on(): return await self.use_answer(driver_path, out)
        self.info(f"Analyze {driver_path}")
        src_base = self.runner.ro_project.repo_dir
        workdir = self.runner.get_workdir(f"{self.name}/{driver_path.name}")
        cwd = self.runner.crs / "fuzzer/syzlang-gen/SyzDescribe/"
        cmd = ["python3", cwd / "main.py"]
        cmd += ["--source_base", src_base]
        cmd += ["--driver_path", driver_path]
        cmd += ["--workdir", workdir]
        cmd += ["--output_file", out]
        await self.async_run_llm(cmd, cwd=cwd, timeout = 300)
        self.info(f"Done {driver_path}")

EMPTY_SYZLANG_CONST = """
# Code generated by syz-sysgen. DO NOT EDIT.
arches = 386, amd64, arm, arm64, mips64le, ppc64le, riscv64, s390x
"""

class HarnessRunner:
    def __init__ (self, runner, submit_id, harness, idx):
        self.submit_id = submit_id
        self.id = f"harness_{idx}"
        self.runner = runner
        self.name = harness["name"]
        self.src = Path(harness["source"])
        self.bin = Path(harness["binary"])
        self.ncpu = {}
        self.workdir = self.runner.workdir / "HarnessRunner" / self.name
        os.makedirs(self.workdir, exist_ok = True)
        self.blob_dir = self.get_workdir("blob_seeds")
        self.blob_priority = self.workdir / "blob_priority.json"
        self.blob_lock = asyncio.Lock()

        self.testlang = None
        self.syzlang = None
        self.built_syzkaller = None

    def get_skytracer_harness(self):
        ret = self.runner.skytracer_harness_dir / self.name
        if ret.exists(): return ret
        return None

    def get_workdir (self, name):
        workdir = self.workdir / name
        os.makedirs(workdir, exist_ok = True)
        return workdir

    def set_ncpu (self, ncpu):
        syzkaller = self.runner.syzkaller
        skyqemu = self.runner.skyqemu
        on_syzkaller = syzkaller.is_on()
        on_skyqemu = skyqemu.is_on()
        ncpu_syzkaller, ncpu_skyqemu = 0, 0
        if on_syzkaller and on_skyqemu:
            if ncpu == 1: ncpu_syzkaller = 1
            elif ncpu == 2:
                ncpu_syzkaller, ncpu_skyqemu = 1, 1
            else:
                ncpu_skyqemu = round(ncpu / 3)
                ncpu_syzkaller = ncpu - ncpu_skyqemu
        elif on_syzkaller: ncpu_syzkaller = ncpu
        elif on_skyqemu: ncpu_skyqemu = ncpu
        self.ncpu[syzkaller.name] = ncpu_syzkaller
        self.ncpu[skyqemu.name] = ncpu_skyqemu

    def info(self, msg):
        logging.info(f"[{self.name}] {msg}")

    async def submit_pov(self, pov):
        await self.runner.commit_analyzer.wait()
        self.info(f"Submit POV {pov}")
        cmd = [self.runner.verifier]
        cmd += ["--harness", self.submit_id]
        cmd += ["--pov", str(pov)]
        return await async_run_cmd(cmd, timeout=30, only_retcode=True) == 0

    async def wait_syzkaller_file(self, path, verbose=False):
        if verbose:
            self.info(f"Wait until {path} is created..")
        while not path.exists():
            if self.built_syzkaller == False: return False
            await asyncio.sleep(1)
        return True

    async def update_blob_priority(self, priority_map, need_exec):
        if len(priority_map) == 0: return
        async with self.blob_lock:
            cur = {}
            if self.blob_priority.exists():
                with open(self.blob_priority) as f: cur = json.load(f)
            for name, p in priority_map.items():
                cur[name] = [p, not need_exec]
            with open(self.blob_priority, "wt") as f: json.dump(cur, f)

    async def to_blob_dir(self, seed_dir, priority):
        if not (seed_dir.exists() and seed_dir.is_dir()):
            self.info(f"Skip to_blob_dir, seed_dir does not exists {seed_dir}, priority: {priority}")
            return
        self.info(f"to_blob_dir {seed_dir}, priority: {priority}")
        pmap = {}
        for name in os.listdir(str(seed_dir)):
            name = seed_dir / name
            new = self.blob_dir / file_hash(name)
            pmap[new.name] = priority
            await async_run_cmd(["mv", name, new])
        await self.update_blob_priority(pmap, True)

    async def hybrid_sync_seeds(self, seed_dir):
        if not self.syzlang:
            return self.info("Skip sync seeds because there is not syzlang")
        if not self.runner.syzkaller.is_on():
            return self.info("Skip sync seeds because syzkaller is disabled")
        if not seed_dir.exists() or len(os.listdir(str(seed_dir))) == 0:
            return self.info(f"Skip sync seeds because {seed_dir} is empty")
        syzkaller = self.workdir / "syzkaller"
        blob2syz = syzkaller / "bin/syz-blob2syz"
        manager = syzkaller / "bin/syz-manager"
        conf = syzkaller / "config.cfg"
        if not await self.wait_syzkaller_file(manager): return
        if not await self.wait_syzkaller_file(blob2syz): return
        if not await self.wait_syzkaller_file(conf): return
        if self.built_syzkaller == False: return
        self.info(f"Sync seeds at {seed_dir}")
        env = os.environ.copy()
        env["PATH"] += f":{syzkaller/'bin'}"
        cmd = [blob2syz]
        cmd += ["-syzlang", self.syzlang]
        cmd += ["-blob-dir", seed_dir]
        cmd += ["-syz-conf", conf]
        await async_run_cmd(cmd, env=env)
        syzdb = syzkaller / "bin/syz-db"
        cmd = [syzdb, "unpack-blobs", syzkaller / "work/corpus.db", seed_dir]
        await async_run_cmd(cmd, env=env)
        score = syzkaller / "work/score.json"
        if score.exists():
            with open(score, "r") as f : score = json.load(f)
            await self.update_blob_priority(score, False)

    async def infer_testlang(self):
        self.testlang = await self.runner.reverser.async_run(self)

    async def infer_syzlang(self):
        await self.runner.wait_syzlang_gen()
        self.syzlang = await self.runner.syz_reverser.async_run(self)
        syzlang_const = str(self.syzlang) + ".const"
        with open (syzlang_const, "wt") as f:
            f.write(EMPTY_SYZLANG_CONST)
        self.syzlang_const = syzlang_const

    async def convert_pocs(self, poc_dir):
        pov, tmp_seeds = await self.runner.converter.convert(self, poc_dir, True)
        if pov == None or tmp_seeds == None: return
        await self.to_blob_dir(tmp_seeds, 0)

    async def convert_seeds(self, seeds):
        seeds, tmp_seeds = await self.runner.converter.convert(self, seeds, False)
        if seeds == None or tmp_seeds == None: return
        await self.to_blob_dir(seeds, 10)
        await self.to_blob_dir(tmp_seeds, 0)

    async def run_hybrid(self):
        is_built = await self.runner.syzkaller.build(self)
        self.built_syzkaller = is_built
        jobs = []
        if is_built:
            t1 = asyncio.create_task(self.runner.syzkaller.async_run(self))
            jobs.append(t1)
        else:
            self.info("Fail to build syzkaller")
            self.ncpu[self.runner.skyqemu.name]+=self.ncpu[self.runner.syzkaller.name]
            self.ncpu[self.runner.syzkaller.name] = 0
            self.info("Allocate NCPU from syzkaller to skyqemu")
        await self.to_blob_dir(self.workdir / "syz-reverser/seeds", 0)
        t2 = asyncio.create_task(self.runner.skyqemu.async_run(self))
        jobs.append(t2)
        await asyncio.gather(*jobs)

def is_kernel_build(base):
    return (base / "arch/x86/boot/bzImage").exists()

class Runner:
    def __init__ (self, project, build_dir, workdir):
        self.llm_init_spend = asyncio.run(get_llm_spend())
        self.workdir = workdir
        os.makedirs(str(workdir), exist_ok=True)
        if CONFIG.build_cache:
            self.build_dir = build_dir
        else:
            run_cmd(["rm", "-rf", f"{build_dir}/*"])
            self.build_dir = workdir
        self.ro_project = None
        if CONFIG.is_main():
            self.project = project.clone(build_dir / "cp-linux")
        self.crs = Path("/home/crs-cp-linux")
        self.verifier = self.crs / "verifier/verifier.py"

        self.reverser = Reverser(self)
        self.cve_analyzer = CVE_Analyzer()
        self.converter = Converter()
        self.syz_reverser = SyzReverser()
        self.syzkaller = Syzkaller()
        self.commit_analyzer = Commit_Analyzer()
        self.seed_selector = Seed_Selector()
        self.skyqemu = SkyQEMU()
        self.seed_generator = Seed_Generator(self)
        self.syzlang_generator = Syzlang_Generator(self)

        self.modules = [
            self.reverser,
            self.syz_reverser,
            self.cve_analyzer,
            self.converter,
            self.syzkaller,
            self.commit_analyzer,
            self.seed_selector,
            self.skyqemu,
            self.seed_generator,
            self.syzlang_generator
        ]

        self.llm_lock = None
        self.skytracer_kernel = None
        self.skytracer_harness_dir = None
        self.harness_dir = None
        self.init_kernel = None
        self.latest_kernel = None
        self.syzkaller_kernel = None
        self.prepare_try = {}

        self.poc_dir = None
        self.seed_dir = None
        self.cve_commits = None
        self.syzlang_dir = None
        self.prepared = False

        self.check_config()

    def check_config(self):
        BAR()
        logging.info("Running options:")
        logging.info(f"Use build cache: {CONFIG.build_cache}")
        logging.info(f"Target Harness: {CONFIG.target_harness}")
        logging.info(f"# of cores: {CONFIG.ncpu}")
        logging.info(f"# of llm_lock: {CONFIG.n_llm_lock}")
        for m in self.modules: m.check_on()
        BAR()

    def load_ro_project(self, project):
        self.ro_project = project.clone(self.workdir / "ro-cp-linux")

    def get_workdir (self, name):
        workdir = self.workdir / name
        os.makedirs(workdir, exist_ok = True)
        return workdir

    def get_harness_bin(self, submit_id):
        harness = self.ro_project.get_harnesses()[submit_id]
        return self.harness_dir / (Path(harness["binary"]).name)

    async def check_result(self, interval = 60):
        while True:
            await asyncio.sleep(interval)
            cmd = [self.verifier, "--check"]
            await async_run_cmd(cmd)

    async def llm_total_spend(self):
        spend = await get_llm_spend()
        return spend - self.llm_init_spend

    async def llm_log(self, msg=""):
        spend = await self.llm_total_spend()
        logging.info(f"Total LLM Spend: {spend} {msg}")

    async def check_llm_usage(self, interval=60):
        while True:
            await asyncio.sleep(interval)
            await self.llm_log()

    def get_shared_path(self, path):
        shared_dir = self.build_dir / "shared_output"
        os.makedirs(shared_dir, exist_ok = True)
        return shared_dir / path.name

    async def to_shared_file(self, src):
        dst = self.get_shared_path(src)
        await async_copy(src, dst)
        return SharedFile(dst).finalize()

    async def from_shared_file(self, dst):
        src = self.get_shared_path(dst)
        shared_src = SharedFile(src)
        await shared_src.async_wait()
        await async_copy(src, dst)
        if dst.exists():
            logging.info(f"Successfully copy from shared file: {src} => {dst}")
            return dst
        else:
            logging.info(f"Fail to copy from shared file: {src} => {dst}")
            return None

    def get_added_drivers(self):
        proj = self.ro_project
        repo = proj.repo
        last = repo.commit(proj.commits[0])
        first = repo.commit(proj.commits[-1])
        ret = []
        for diff in first.diff(last):
            if diff.change_type != "A": continue
            path = diff.a_path
            names = path.split("/")
            if len(names) != 3: continue
            if names[0] == "drivers"  and names[-1] == "Makefile":
                driver = names[0] + "/" + names[1]
                ret.append(driver)
        return list(set(ret))

    async def __syzlang_gen(self, syzlang_dir):
        jobs = []
        for driver in self.get_added_drivers():
            driver = Path(driver)
            jobs.append(self.syzlang_generator.async_run(driver, syzlang_dir))
        await asyncio.gather(*jobs)
        logging.info("Generated Syzlangs: " + " ".join(os.listdir(syzlang_dir)))
        await self.verify_syzlang(syzlang_dir)
        await self.finalize_syzlang(syzlang_dir)

    async def syzlang_gen(self):
        syzlang_dir = self.get_workdir("syzlangs")
        if CONFIG.is_main():
            await self.__syzlang_gen(syzlang_dir)
            await self.to_shared_file(syzlang_dir)
        if CONFIG.is_worker():
            await self.from_shared_file(syzlang_dir)
            await self.finalize_syzlang(syzlang_dir)
        self.syzlang_dir = syzlang_dir

    async def verify_syzlang(self, syzlang_dir):
        syzkaller = self.syzkaller.get_root_dir(self)
        syz_reverser = self.syz_reverser.get_syzkaller_dir(self)
        MAKE_DES = ["make", "descriptions"]
        syzlangs = glob.glob(f"{syzlang_dir}/*.txt")
        if len(syzlangs) == 0: return
        for old_path in syzlangs:
            old_path = Path(old_path)
            new_path = syzkaller / "sys/linux" / old_path.name
            await async_copy_file(old_path, new_path)
            logging.info(f"Verify {old_path.name}")
            ret = await async_run_cmd(MAKE_DES, cwd=syzkaller, only_retcode = True)
            if ret != 0:
                logging.info(f"Removing {new_path} due to a compile error")
                await async_remove_file(new_path)
                await async_remove_file(old_path)
            else:
                new_path = syz_reverser / "sys/linux" / old_path.name
                await async_copy_file(old_path, new_path)

    async def finalize_syzlang(self, syzlang_dir):
        syzkaller = self.syzkaller.get_root_dir(self)
        syz_reverser = self.syz_reverser.get_syzkaller_dir(self)
        syzlangs = glob.glob(f"{syzlang_dir}/*.txt")
        if len(syzlangs) == 0: return
        MAKE_GEN = ["make", "generate"]
        MAKE_REV = ["make", "reverser"]
        logging.info(f"Finalize all filtered syzlangs again")
        r1 = await async_run_cmd(MAKE_GEN, cwd = syzkaller, only_retcode=True)
        r2 = await async_run_cmd(MAKE_GEN, cwd = syz_reverser, only_retcode=True)
        r3 = await async_run_cmd(MAKE_REV, cwd = syz_reverser, only_retcode=True)
        if r1 != 0 or r2 != 0 or r3 != 0:
            for old_path in syzlangs:
                await async_remove_file(syzkaller / "sys/linux" / old_path.name)
                await async_remove_file(syz_reverser / "sys/linux" / old_path.name)
                await async_remove_file(old_path)
            return logging.info("Verify syzlang fail: remove all generated syzlang")

    def prepare_tried (self, name):
        if name in self.prepare_try: return True
        self.prepare_try[name] = True
        return False

    def prepare_skytracer(self):
        if self.prepare_tried("skytracer"): return
        logging.info("Build kernel for SkyTracer")
        out = self.build_dir / "skytracer-linux"
        harness_dir = self.build_dir / "sky-harness"
        os.makedirs(str(harness_dir), exist_ok=True)
        skytracer = self.crs / "fuzzer/SkyTracer/"
        if not (CONFIG.build_cache and is_kernel_build(out)) and CONFIG.is_main():
            self.project.checkout(0)
            cmd = ["./prepare_kernel.py", "--instrument", self.project.repo_dir]
            run_cmd(cmd, cwd = str(skytracer))
            instrument = skytracer / "prepare_target.py"
            for (_, cur) in self.project.harnesses.items():
                run_cmd([instrument, "--src", cur["source"]])
            self.project.build(0, out, False)
            for (_, cur) in self.project.harnesses.items():
                bin = Path(cur["binary"])
                dst = harness_dir / bin.name
                rename(bin, str(dst))
            vmlinux  = self.project.repo_dir / "vmlinux"
            if vmlinux.exists():
                cmd = ["./prepare_kernel.py", "--symtabs", vmlinux]
                run_cmd(cmd, cwd = str(self.crs / "fuzzer" / "SkyTracer"))
                SYMTABS = "vmlinux.symtabs"
                rename(self.project.repo_dir / SYMTABS, out / SYMTABS)
            SharedFile(out).finalize()
            SharedFile(harness_dir).finalize()

        if CONFIG.is_worker():
            SharedFile(out).wait()
            SharedFile(harness_dir).wait()

        if is_kernel_build(out):
            logging.info("Build kernel for SkyTracer successfully")
            self.skytracer_harness_dir = self.__artifact_to_workdir(harness_dir)
            self.skytracer_kernel = self.__artifact_to_workdir(out)
        else: logging.error("Fail to build kernel for SkyTracer")

    def prepare_syzkaller(self):
        if self.prepare_tried("syzkaller"): return
        logging.info("Build kernel for Syzkaller")
        out = self.build_dir / "syzkaller-linux"
        harness_dir = self.build_dir / "harness"
        os.makedirs(harness_dir, exist_ok=True)
        if not (CONFIG.build_cache and is_kernel_build(out)) and CONFIG.is_main():
            self.project.checkout(0)
            conf_path = self.project.repo_dir / ".config"
            with open(conf_path, "rt") as f: conf = f.read()
            with open(conf_path, "wt") as f:
                conf += "\n"
                conf += "CONFIG_KCOV=y\n"
                conf += "CONFIG_DEBUG_INFO_DWARF4=y\n"
                conf += "CONFIG_CONFIGFS_FS=y\n"
                conf += "CONFIG_SECURITYFS=y\n"
                f.write(conf)
            self.project.build(0, out, False, copy_vmlinux=True)
            for (_, cur) in self.project.harnesses.items():
                bin = Path(cur["binary"])
                dst = harness_dir / bin.name
                rename(bin, str(dst))
            SharedFile(out).finalize()
            SharedFile(harness_dir).finalize()

        if CONFIG.is_worker():
            SharedFile(out).wait()
            SharedFile(harness_dir).wait()

        if is_kernel_build(out):
            logging.info("Build kernel for syzkaller successfully")
            self.harness_dir = self.__artifact_to_workdir(harness_dir)
            self.syzkaller_kernel = self.__artifact_to_workdir(out)

    def prepare_init_kernel(self):
        if self.prepare_tried("init_kernel"): return
        logging.info("Build the init kernel")
        out = self.build_dir / "init_kernel"
        if CONFIG.is_main():
            self.project.build(-1, out)
            SharedFile(out).finalize()
        if CONFIG.is_worker():
            SharedFile(out).wait()
        if is_kernel_build(out):
            logging.info("Successfully build init kernel")
            self.init_kernel = self.__artifact_to_workdir(out)

    def prepare_latest_kernel(self):
        if self.prepare_tried("latest_kernel"): return
        logging.info("Build the latest kernel")
        out = self.build_dir / "latest_kernel"
        if CONFIG.is_main():
            self.project.build(0, out)
            SharedFile(out).finalize()
        if CONFIG.is_worker():
            SharedFile(out).wait()
        if is_kernel_build(out):
            logging.info("Successfully build latest kernel")
            self.latest_kernel = self.__artifact_to_workdir(out)

    def __artifact_to_workdir(self, target):
        if target == None: return None
        dst = self.workdir / target.name
        logging.info(f"Copy artifacts to workdir: {target} => {dst}")
        copy_dir(target, dst)
        return dst

    def __precompile_cmd(self):
        logging.info("Send precompile request")
        return [self.verifier, "--precompile"]

    def precompile(self):
        if self.prepared == False: return
        cmd = self.__precompile_cmd()
        run_cmd(cmd)

    async def async_precompile(self):
        if self.prepared == False: return
        cmd = self.__precompile_cmd()
        await async_run_cmd(cmd, timeout=30)

    def prepare(self):
        for m in self.modules:
            m.prepare(self)
        self.prepared = True
        if CONFIG.is_main(): self.precompile()

    def alloc_cpu(self, harnesses):
        ncpu = CONFIG.ncpu
        cnt = len(harnesses)
        avg = int(ncpu / cnt)
        mores = random.sample(range(cnt), ncpu % cnt)
        for h in harnesses: h.set_ncpu(avg)
        for idx in mores: harnesses[idx].set_ncpu(avg + 1)

    def load_changes(self):
        if self.changes is None: return None
        with open(self.changes) as f:
            ret = {}
            data = json.load(f)
            for d in data.values(): ret.update(d)
            return ret

    def load_candidates(self):
        if self.candidates is None: return None
        ret = []
        with open(self.candidates, "rt") as f:
            for line in f.readlines():
                line = line.strip().split(",")
                if len(line) != 4: continue
                line = list(map(lambda x: x.strip(), line))
                ret.append(line)
        return ret

    async def select_seed (self):
        seed_dir = self.workdir / "seed"
        self.changes = await self.commit_analyzer.parse_changes(self)
        self.candidates = await self.commit_analyzer.async_run(self)
        if self.candidates != None: os.environ["BIC_HINTS"] = str(self.candidates)
        self.commit_analyzer.done = True
        await self.async_precompile()
        self.seed_dir = await self.seed_selector.async_run(self)

    async def convert_seeds (self, harness):
        while self.seed_dir == None:
            await asyncio.sleep(1)
        if self.seed_dir.exists():
            await harness.convert_seeds(self.seed_dir)

    async def wait_prepare(self):
        while self.prepared == False:
            await asyncio.sleep(5)

    async def wait_cve_analyzer(self):
        while self.poc_dir == None:
            await asyncio.sleep(1)

    async def wait_syzlang_gen(self):
        while self.syzlang_dir == None:
            await asyncio.sleep(1)

    async def convert_pocs (self, harness):
        await self.wait_cve_analyzer()
        if self.poc_dir.exists():
            await harness.convert_pocs(self.poc_dir)

    async def find_pocs (self):
        self.poc_dir = await self.cve_analyzer.async_run(self)

    async def seed_gen (self, harness):
        await self.commit_analyzer.wait()
        await self.seed_generator.async_run(harness)

    async def run_harness(self, harness):
        await harness.infer_testlang()
        if not harness.testlang: return
        infer_syzlang = asyncio.create_task(harness.infer_syzlang())
        seed_gen = asyncio.create_task(self.seed_gen(harness))
        conv_pocs = asyncio.create_task(self.convert_pocs(harness))
        conv_seeds = asyncio.create_task(self.convert_seeds(harness))
        await self.wait_cve_analyzer()
        await self.commit_analyzer.wait()
        await infer_syzlang
        await self.wait_prepare()
        await harness.run_hybrid()
        await conv_pocs
        await seed_gen
        await conv_seeds
        harness.info("DONE")

    async def run(self):
        self.llm_lock = asyncio.Semaphore(CONFIG.n_llm_lock)
        t0 = asyncio.create_task(self.select_seed())
        t1 = asyncio.create_task(self.find_pocs())
        t2 = asyncio.create_task(self.check_result())
        t3 = asyncio.create_task(self.check_llm_usage())
        t4 = asyncio.create_task(self.syzlang_gen())
        hrunners = []
        idx = 0
        for (submit_id, harness) in self.ro_project.get_harnesses().items():
            logging.info(f"Found harness at {harness}")
            hrunner = HarnessRunner(self, submit_id, harness, idx)
            hrunners.append(hrunner)
            idx += 1
        self.alloc_cpu(hrunners)
        jobs = list(map(self.run_harness, hrunners))
        await asyncio.gather(*jobs)
        logging.info("END Jobs")
        await asyncio.gather(t0, t1, t2, t3, t4)

def load_project(cp_root):
    cp_name = "linux kernel"
    lang = "c"
    for fname in glob.glob(f"{cp_root}/**/project.yaml"):
        try: p = Project(Path(fname).parent)
        except: continue
        if p.name == cp_name and (lang == "" or p.lang == lang):
            return p
        name = p.name.lower()
        if "boot/bzImage" in str(p.raw_info):
            return p
        if "linux" in name or "kernel" in name:
            return p
    logging.info("This is not linux kernel CP")
    sys.exit(0)
    return None

def get_tmp_path(cmd):
    for x in cmd:
        if "/tmp/virtme_ret" in x:
            return x.split("path=")[1].strip()
    return ""

def clean_detached_qemu():
    for pid in psutil.pids():
        try:
            p = psutil.Process(pid)
            name = p.name()
            ppid = p.ppid()
            cmd = p.cmdline()
            if "qemu" in name and ppid == 1:
                os.system(f"kill -9 {p.pid}")
                tmp = get_tmp_path(cmd)
                if tmp.startswith("/tmp/virtme_ret"):
                    os.system(f"rm -rf {tmp}")
        except:
            continue

def qemu_cleaner():
    while True:
        clean_detached_qemu()
        time.sleep(10)

LLM_HOST_KEY = ["AIXCC_LITELLM_HOSTNAME", "LITELLM_URL"]
def sync_envs(keys):
    value = None
    for key in keys:
        value = os.environ.get(key)
        if value != None: break
    for key in keys:
        os.environ[key] = value

def setup_env(workdir, cp_linux):
    sync_envs(LLM_HOST_KEY)
    os.environ["CRS_WORKDIR"] = str(workdir)
    os.environ["TARGET_CP"] = cp_linux.name
    os.environ["TARGET_CP_DIR"] = str(cp_linux.base)

def main(cp_root, build_dir, workdir):
    os.system(f"rm -rf {workdir}/*")
    if not build_dir.exists():
        logging.error(f"Build dir({build_dir}) must be mounted by docker")
        sys.exit(-1)
    build_dir = build_dir / "crs-cp-linux"
    os.makedirs(build_dir, exist_ok = True)
    os.makedirs(workdir, exist_ok = True)
    cp_linux = load_project(cp_root)
    setup_env(workdir, cp_linux)
    CONFIG.load("/crs-linux.config")
    if CONFIG.is_main():
        CONFIG.distribute_job(cp_linux, build_dir)
    else:
        CONFIG.load_job(build_dir)
    runner = Runner(cp_linux, build_dir, workdir)
    Thread(target=runner.prepare).start()
    Thread(target=qemu_cleaner).start()
    runner.load_ro_project(cp_linux)
    asyncio.run(runner.run())
    logging.info("END")
    if CONFIG.debug:
        logging.info("Wait until CTRL + C")
        while True:
            time.sleep(1)

if __name__ == "__main__":
    logging.info("Start")
    parser = argparse.ArgumentParser()
    parser.add_argument("--cp-root", help="cp-root directory")
    parser.add_argument("--build-dir", help="build dir")
    args = parser.parse_args()
    workdir = os.environ.get("CRS_WORKDIR", "/crs-workdir/")
    main(Path(args.cp_root), Path(args.build_dir), Path(workdir))
