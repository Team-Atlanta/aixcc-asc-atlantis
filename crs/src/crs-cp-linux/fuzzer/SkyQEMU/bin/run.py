#!/usr/bin/env python3

import os
import sys
from pwn import process
import argparse
from pathlib import Path
from multiprocessing import Process, Manager, Lock
from multiprocessing.managers import SyncManager
from queue import PriorityQueue
import time
import hashlib
import subprocess
import random
import yaml
import json

SKYQEMU = Path(os.path.dirname(__file__)) / "../out" / "qemu-system-x86_64"
VERIFIER =str(Path(os.path.dirname(__file__)) / "../../../verifier/verifier.py")
GUEST_DIR = Path("/tmp/skyqemu/")

def file_hash(fname):
    with open(str(fname), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()

LOWEST = 0
class QueuedSeed:
    def __init__(self, path, priority, sym_executed, conc_executed, scored):
        self.path = path
        self.priority =  priority
        self.sym_executed = sym_executed
        self.conc_executed = conc_executed
        self.scored = scored

    def is_done(self): return self.sym_executed and self.conc_executed

    def update(self, score):
        self.priority = score[0]
        self.conc_executed |= score[1]
        self.scored = True

    def __lt__(self, other):
        return self.priority > other.priority

class SkyQEMU:
    def __init__(self, workdir, runner):
        self.runner = runner
        self.timeout = runner.timeout
        self.kernel = runner.kernel
        self.kasan_kernel = runner.kasan_kernel
        self.workdir = workdir
        self.out_dir = self.workdir / "output"
        self.guest_dir = self.workdir / "guest"
        self.cov = runner.cov
        os.makedirs(self.out_dir, exist_ok = True)
        os.makedirs(self.guest_dir, exist_ok = True)
        self.blob_path = self.guest_dir / "blob"
        self.target = runner.target
        os.system(f"cp {self.target} {self.guest_dir / self.target.name}")

    def log(self, msg):
        with open(self.workdir / "log", "at+") as f: f.write(str(msg) + "\n")

    def __run(self, cmd):
        args  = ["virtme-run", "--memory", "2G", "--mods=auto", "--kopt", "panic=-1"]
        args += ["--kopt", "panic_on_warn=1"]
        args += ["--kopt", "nokaslr"]
        args += ["--kimg", str(self.kernel / "arch/x86/boot/bzImage")]
        args += ["--qemu-bin", str(SKYQEMU)]
        args += ["--rwdir", f"{GUEST_DIR}={self.guest_dir}"]
        args += ["--disable-kvm", "--no-virtme-ng-init"]
        args += ["--script-sh", f"timeout {self.timeout} {cmd}"]

        env = dict(os.environ)
        env["SYMTABS"] = str(self.kernel / "vmlinux.symtabs")
        env["SKYQEMU_OUTPUT_DIR"] = str(self.out_dir)
        env["SKYQEMU_AFL_COVERAGE_MAP"] = str(self.cov)
        proc = process(args, env = env, alarm = self.timeout + 30)
        proc.wait_for_close()

    def __run_concrete(self, cmd):
        args  = ["virtme-run", "--memory", "2G", "--mods=auto", "--kopt", "panic=-1"]
        args += ["--kopt", "panic_on_warn=1", "--kopt", "nokaslr"]
        args += ["--show-boot-console", "--verbose"]
        args += ["--kimg", str(self.kasan_kernel / "arch/x86/boot/bzImage")]
        args += ["--rwdir", f"{GUEST_DIR}={self.guest_dir}"]
        args += ["--no-virtme-ng-init"]
        args += ["--script-sh", f"timeout {self.timeout} {cmd}"]
        try:
            proc = subprocess.run(args, timeout = self.timeout, capture_output=True)
            ret = proc.stdout + proc.stderr
            return ret.decode("utf-8", errors="ignore")
        except: return ""

    def run_concrete(self, seed):
        os.system(f"cp {seed.path} {self.blob_path}")
        cmd = f"{GUEST_DIR / self.target.name} {GUEST_DIR / self.blob_path.name}"
        ret = self.__run_concrete(cmd)
        return self.runner.run_verifier(ret, seed)

    def symexec(self, seed, dst_dir):
        os.system(f"cp {seed.path} {self.blob_path}")
        cmd = f"{GUEST_DIR / self.target.name} {GUEST_DIR / self.blob_path.name}"
        self.__run(cmd)
        for new in os.listdir(self.out_dir):
            new = self.out_dir / new
            if new.stat().st_size == 0:
                os.system(f"rm {new}")
                continue
            dst = dst_dir / file_hash(new)
            os.system(f"mv {new} {dst}")

class Runner:
    def __init__(self, args):
        self.ncpu = args.ncpu
        self.workdir = args.workdir
        self.seed_dir = args.seed_dir
        self.kernel = args.kernel
        self.kasan_kernel = args.kasan_kernel
        self.cov = args.workdir / "cov"
        self.target = args.target
        self.timeout = args.timeout
        self.harness_id = args.harness_id
        self.skyqemus = []
        with open(args.proj, "r") as f:
            self.sanitizers = yaml.safe_load(f)["sanitizers"]

        for i in range(self.ncpu):
            workdir = self.workdir / str(i)
            os.makedirs(workdir, exist_ok=True)
            self.skyqemus.append(SkyQEMU(workdir, self))
        SyncManager.register("PriorityQueue", PriorityQueue)
        self.manager = Manager()
        self.sym_q = self.manager.PriorityQueue()
        self.run_q = self.manager.PriorityQueue()
        self.queued = self.manager.dict() # name -> QueuedSeed
        self.verified = self.manager.dict()

    def load_score(self):
        fname = self.seed_dir / "../blob_priority.json"
        if not fname.exists(): return {}
        with open(fname) as f:
            return json.load(f)

    def check_sanitizer(self, ret):
        for san in self.sanitizers.values():
            if san in ret:
                ret = ret[ret.index(san):]
                ret = ret[:ret.index("\n")]
                return ret
        return None

    def run_verifier(self, ret, pov):
        ret = self.check_sanitizer(ret)
        if ret is None: return False
        if ret in self.verified: return False
        self.verified[ret] = True
        cmd = [VERIFIER, "--harness", str(self.harness_id), "--pov", str(pov.path)]
        try: subprocess.check_output(cmd)
        except: pass
        return True

    def put_sym_q(self, queued_seed):
        if queued_seed.sym_executed: return
        self.sym_q.put(queued_seed)

    def put_run_q(self, queued_seed):
        if queued_seed.conc_executed: return
        self.run_q.put(queued_seed)

    def sync_seed(self, sleep_time=10):
        last = 0
        while True:
            if last + sleep_time > time.time():
                time.sleep(sleep_time)
                continue
            last = time.time()
            scores = self.load_score()
            for seed_name in os.listdir(str(self.seed_dir)):
                seed = self.seed_dir / seed_name
                if seed_name not in self.queued:
                    queued_seed = None
                    if seed_name in scores:
                        score = scores[seed_name]
                        queued_seed = QueuedSeed(seed, score[0], False, score[1], True)
                    else: queued_seed = QueuedSeed(seed, LOWEST, False, False, False)
                    self.queued[seed_name] = queued_seed
                    self.put_sym_q(queued_seed)
                    self.put_run_q(queued_seed)
                else:
                    queued_seed = self.queued[seed_name]
                    if queued_seed.is_done(): continue
                    if seed_name in scores:
                        queued_seed.update(scores[seed_name])
                        self.queued[seed_name] = queued_seed
                        self.put_sym_q(queued_seed)
                        self.put_run_q(queued_seed)

    def loop(self):
        procs = [Process(target=self.sync_seed)]
        for skyqemu in self.skyqemus:
            procs.append(Process(target=self.run_each, args=(skyqemu,)))
        for proc in procs: proc.start()
        for proc in procs: proc.join()

    def run_sym(self, skyqemu):
        try: seed = self.sym_q.get(False)
        except: return False
        qseed = self.queued[seed.path.name]
        if qseed.sym_executed: return True
        qseed.sym_executed = True
        self.queued[seed.path.name] = qseed
        skyqemu.symexec(seed, self.seed_dir)
        return True

    def run_concrete(self, skyqemu, n = 5):
        n = random.randint(1, n)
        for _ in range(n):
            try: seed = self.run_q.get(False)
            except: return False
            qseed = self.queued[seed.path.name]
            if qseed.conc_executed: continue
            qseed.conc_executed = True
            self.queued[seed.path.name] = qseed
            skyqemu.run_concrete(seed)
        return False

    def run_each(self, skyqemu, sleep_time=10):
        while True:
            done_concrete = self.run_concrete(skyqemu)
            done_sym = self.run_sym(skyqemu)
            if not done_sym and not done_concrete:
                time.sleep(sleep_time)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ncpu", type=int, help="# of cpu", default = 1)
    parser.add_argument("--kernel", type=Path, help="kernel", required=True)
    parser.add_argument("--kasan-kernel", type=Path, help="kasan kernel", required=True)
    parser.add_argument("--proj", type=Path, help="proj yaml", required=True)
    parser.add_argument("--target", type=Path, help="target bin", required=True)
    parser.add_argument("--seed-dir", type=Path, help="seed_dir", required=True)
    parser.add_argument("--workdir", type=Path, help="workdir", default="/tmp/skyqemu")
    parser.add_argument("--harness-id", type=Path, help="harness id", required=True)
    parser.add_argument("--timeout", type=int, help="timeout for analyzing each seed", default=60)
    args = parser.parse_args()
    os.system(f"rm -rf {args.workdir}")
    runner = Runner(args)
    runner.loop()
