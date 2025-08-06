import os
import shutil
import subprocess
from pathlib import Path

from .kasan_report_parser import KasanReport, kasan_parse

TIMEOUT = 240
OK_STRING = "================OK================"


class KasanRunner:
    def __init__(self, kernel: Path, workdir: Path):
        os.makedirs(workdir, exist_ok=True)
        self.workdir = Path(workdir)
        self.kernel = Path(kernel)

    def exec_target(self, target_bin_path: Path, blob_path: Path, timeout=TIMEOUT) -> KasanReport:
        temp_sh = self.workdir / "script.sh"
        temp_bin = self.workdir / target_bin_path.name
        temp_blob = self.workdir / "blob"
        shutil.copy(target_bin_path, temp_bin)
        shutil.copy(blob_path, temp_blob)

        with open(temp_sh, "w") as f:
            f.write(f"#!/bin/bash\ntimeout {timeout} {temp_bin} {temp_blob} && echo {OK_STRING}\n")

        os.chmod(temp_sh, 0o550)
        os.chmod(temp_bin, 0o550)

        args = [
            "virtme-run",
            "--verbose",
            "--show-boot-console",
            "--memory",
            "2G",
            "--mods=auto",
            "--kopt",
            "panic=-1",
            "--kopt",
            "panic_on_warn=1",
            "--script-sh",
            temp_sh,
            "--kimg",
            str(self.kernel / "arch/x86/boot/bzImage"),
            "--qemu-opts",
            "--enable-kvm",
        ]

        env = dict(os.environ)
        try:
            handle = subprocess.run(
                args,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                start_new_session=True,
                shell=False,
                bufsize=0,
                env=env,
                timeout=timeout + 60,
            )
            stderr_data = handle.stderr.decode("utf-8", errors="ignore")
            stdout_data = handle.stdout.decode("utf-8", errors="ignore")
            timed_out = True
            if OK_STRING in stdout_data:
                timed_out = False
            return kasan_parse(stderr_data, timed_out)
        except subprocess.TimeoutExpired as e:
            if e.stderr is not None:
                stderr_data = e.stderr.decode("utf-8", errors="ignore")
                return kasan_parse(stderr_data, True)
            return kasan_parse("", True)
