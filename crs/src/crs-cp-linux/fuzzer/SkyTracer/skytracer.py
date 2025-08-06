#!/usr/bin/env python3
import argparse
import datetime
import os
import subprocess
import time
import shutil
from pathlib import Path
import pwn
import threading

if __name__ == "__main__":
    from trace import load_trace
else:
    from .trace import load_trace


SKYTRACER = Path(os.path.dirname(__file__)) / "out" / "qemu-system-x86_64"
PRE_SHELL = b"root@(none):/#"
GUEST_DIR = Path("/tmp/tracer/")
TRACER_INSTRUMENT = """
static void skytracer_init(int argc, char **argv, char **envp) {
  asm("mov $0xf000, %rax; syscall");
}

static void skytracer_fini(void) {
  asm("mov $0xf001, %rax; syscall");
}

__attribute__((section(".init_array"), used)) static typeof(skytracer_init) *init_p = skytracer_init;
__attribute__((section(".fini_array"), used)) static typeof(skytracer_fini) *fini_p = skytracer_fini;
"""
TIMEOUT=60
HANG_TIMEOUT=5
MONITOR_INTERVAL=1

def load_symtabs(path):
    ret = {}
    with open (path, "rt") as f:
        for line in f.read().split("\n")[:-1]:
            tmp = line.split(",")
            name = tmp[0]
            addr = int(tmp[1], 16)
            ret[addr] = name
    return ret

class SkyTracer:
    def __init__(self, kernel, workdir, monitor=False):
        os.makedirs(workdir, exist_ok = True)
        self.workdir = Path(workdir)
        self.out_path = self.workdir / "trace"
        self.kernel = Path(kernel)
        self.symtabs = self.kernel / "vmlinux.symtabs"
        if not self.symtabs.exists():
            raise Exception(f"{self.symtabs} does not exists")
        self.running = False
        if monitor:
            self.monitor = threading.Thread(target=self.monitor)
            self.monitor.start()

    def __boot_kernel(self):
        args  = ["virtme-run", "--memory 2G", "--mods=auto", "--kopt", "panic=-1"]
        args += ["--kopt", "nokaslr"]
        args += ["--kimg", str(self.kernel / "arch/x86/boot/bzImage")]
        args += ["--qemu-bin", str(SKYTRACER)]
        args += ["--rwdir", f"{GUEST_DIR}={self.workdir}"]
        args += ["--disable-kvm"]
        args += ["--no-virtme-ng-init"]

        cmd = " ".join(args)
        env = dict(os.environ)
        env["SYMTABS"] = str(self.symtabs)
        env["SKYTRACE_OUT"] = str(self.out_path)
        proc = pwn.process(cmd, shell=True, env=env)
        proc.recvuntil(PRE_SHELL)
        return proc

    def __run(self, cmd, timeout=TIMEOUT):
        if self.proc.poll() is not None:
            self.proc = self.__boot_kernel()
        if isinstance(cmd, str): cmd = bytes(cmd, "utf-8")
        cmd = f"timeout {timeout} ".encode() + cmd
        self.running = True
        self.proc.sendline(cmd)
        output = self.proc.recvuntil(PRE_SHELL)[:-len(PRE_SHELL)]
        self.running = False
        return output

    def prepare_target(self, target_src):
        target_src = Path(target_src)
        name = target_src.name
        if not name.endswith(".c"):
            raise Exception(f"target ({target_src}) must endwith `.c`")
        with open(target_src, "rt") as f : code = f.read()
        code += TRACER_INSTRUMENT
        target_src = self.workdir / name
        with open(target_src, "wt") as f: f.write(code)
        target_bin = self.workdir / name[:-2]
        print("[WARNING] TODO: We must use build.sh later")
        os.system(f"gcc {target_src} -static -o {target_bin}")
        if not target_bin.exists():
            raise Exception(f"Compile {target_src} fail")

        return target_bin

    def trace_target(self, target_bin, blob: bytes, timeout=TIMEOUT):
        self.run_target(target_bin, blob, timeout=timeout)
        trace = load_trace(self.out_path)
        return trace

    def run_target(self, target_bin, blob: bytes, timeout=TIMEOUT):
        target_bin = Path(target_bin)
        if not target_bin.exists():
            raise Exception(f"Execute prepare_target first!: {target_bin} does not exist")
        try:
            shutil.copy2(target_bin, self.workdir / target_bin.name)
        except shutil.SameFileError:
            pass
        blob_path = self.workdir / "blob"
        with open (blob_path, "wb") as f: f.write(blob)
        try:
            os.remove(self.out_path)
        except FileNotFoundError:
            pass
        cmd = f"{GUEST_DIR / target_bin.name} {GUEST_DIR / blob_path.name}"
        try:
            print(self.__run(cmd, timeout=timeout))
        except Exception as e:
            print(e)
        os.remove(blob_path)

    def __enter__(self):
        self.proc = self.__boot_kernel()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        proc = self.proc
        sid = os.getsid(proc.proc.pid)
        while proc.poll() is None:
            os.system(f"pkill -s {sid}")
            time.sleep(0.1)

    def monitor(self):
        while True:
            try:
                time.sleep(MONITOR_INTERVAL)
                if not self.running:
                    continue
                hang_time = time.time() - self.out_path.stat().st_mtime
                print(f"[MONITOR] Hang for {hang_time}s ...")
                if hang_time < HANG_TIMEOUT:
                    continue
                print("[MONITOR] Killing ...")
                self.running = False
                self.__exit__(None, None, None)
            except Exception as e:
                print(e)
                pass

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel",
                        help="path to the kernel directory for SkyTracer")
    parser.add_argument("target",
                        help="path to the target source or binary")
    parser.add_argument("--workdir", default="/tmp/tracer",
                        help="path to the working directory")
    parser.add_argument("--no_load", action="store_true")
    parser.add_argument("--timeout", default=TIMEOUT)
    parser.add_argument("--monitor", action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print(args)
    print("Starting SkyTracer ...")
    with SkyTracer(args.kernel, args.workdir, args.monitor) as t:
        funcs = load_symtabs(t.symtabs)
        target = args.target
        if target.endswith(".c"):
            target = t.prepare_target(target)
        print("SkyTracer is ready")
        while True:
            blob = input("Enter the blob path:\n")
            with open (blob, "rb") as f: data = f.read()
            t.run_target(target, data, timeout=args.timeout)
            print("Here is the trace path:")
            print(t.out_path)
            if not args.no_load:
                trace = load_trace(t.out_path)
                os.remove(t.out_path)
                print(datetime.datetime.now())
                print(trace.str(funcs))
