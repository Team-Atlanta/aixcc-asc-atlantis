from __future__ import annotations

import asyncio
import contextlib
import enum
import os
from pathlib import Path
import re
from typing import Any

from git import Repo
from structlog.stdlib import get_logger
from vyper import v

from competition_api.audit import Auditor
from competition_api.audit.types import EventType, TimeoutContext
from competition_api.cp_registry import CPRegistry
from competition_api.flatfile import Flatfile
from competition_api.sadlock import test_and_set

LOGGER = get_logger(__name__)


DOCKER_READY_CHECK_INTERVAL = 2
SPURIOUS_FAILURE_ATTEMPTS = 3
SPURIOUS_FAILURE_INDICATORS = [
    # [    0.157407] ==================================================================
    # [    0.158288] BUG: KASAN: wild-memory-access in ct_nmi_enter+0x9c/0x190
    # [    0.158399] Read of size 4 at addr ff1100006ce32cc0 by task swapper/0/0
    # [    0.158399]
    # [    0.158399] CPU: 0 PID: 0 Comm: swapper/0 Not tainted 6.1.54-gfc6c3e1d7deb #2
    # [    0.158399] Hardware name: QEMU Standard PC (i440FX + PIIX, 1996), BIOS 1.15.0-1 04/01/2014
    # [    0.158399] Call Trace:
    # [    0.158399]  <TASK>
    # [    0.158399]  dump_stack_lvl+0x34/0x48
    # [    0.158399]  ? ct_nmi_enter+0x9c/0x190
    # [    0.158399]  kasan_report+0xad/0x130
    # [    0.158399]  ? ct_nmi_enter+0x9c/0x190
    # [    0.158399]  kasan_check_range+0x35/0x1c0
    # [    0.158399]  ct_nmi_enter+0x9c/0x190
    # [    0.158399]  irqentry_enter+0x30/0x40
    # [    0.158399]  common_interrupt+0x15/0xc0
    # [    0.158399]  asm_common_interrupt+0x22/0x40
    # [    0.158399] RIP: 0010:get_cpu_cap+0xe0/0xc30
    # [    0.158399] Code: 14 02 4c 89 f8 83 e0 07 83 c0 03 38 d0 7c 08 84 d2 0f 85 dd 09 00 00 83 7d 24 05 0f 8e 1c 08 00 00 b8 06 00 00 00 31 c9 0f a2 <48> ba 00 00 00 00 00 fc ff df 48 8d 7d 60 48 89 f9 48 c1 e9 03 0f
    # [    0.158399] RSP: 0000:ffffffffb8007e50 EFLAGS: 00000246
    # [    0.158399] RAX: 0000000000000004 RBX: 0000000000000000 RCX: 0000000000000000
    # [    0.158399] RDX: 0000000000000000 RSI: 1ffffffff719a63b RDI: ffffffffb8cd31d8
    # [    0.158399] RBP: ffffffffb8cd31a0 R08: 0000000000000001 R09: 0000000000000000
    # [    0.158399] R10: ffffffffb8cd31a8 R11: 0000000000000001 R12: ffffffffb8cd3238
    # [    0.158399] R13: ffffffffb8cd31a0 R14: ffffffffb8cd31c8 R15: ffffffffb8cd31c4
    # [    0.158399]  ? get_cpu_vendor+0x8c/0x280
    # [    0.158399]  identify_cpu+0x35c/0x1d00
    # [    0.158399]  ? mutex_unlock+0x7b/0xd0
    # [    0.158399]  ? __mutex_unlock_slowpath.constprop.0+0x2a0/0x2a0
    # [    0.158399]  ? jump_label_update+0x11b/0x360
    # [    0.158399]  identify_boot_cpu+0xd/0xb5
    # [    0.158399]  arch_cpu_finalize_init+0x5/0xa1
    # [    0.158399]  start_kernel+0x314/0x3b7
    # [    0.158399]  secondary_startup_64_no_verify+0xe0/0xeb
    # [    0.158399]  </TASK>
    # [    0.158399] ==================================================================
    # [    0.158399] Kernel panic - not syncing: KASAN: panic_on_warn set ...
    # [    0.158399] CPU: 0 PID: 0 Comm: swapper/0 Not tainted 6.1.54-gfc6c3e1d7deb #2
    # [    0.158399] Hardware name: QEMU Standard PC (i440FX + PIIX, 1996), BIOS 1.15.0-1 04/01/2014
    # [    0.158399] Call Trace:
    # [    0.158399]  <TASK>
    # [    0.158399]  dump_stack_lvl+0x34/0x48
    # [    0.158399]  panic+0x228/0x479
    # [    0.158399]  ? panic_print_sys_info.part.0+0x4d/0x4d
    # [    0.158399]  ? snapshot_read.cold+0x1d/0x1d
    # [    0.158399]  check_panic_on_warn.cold+0x14/0x2b
    # [    0.158399]  end_report.part.0+0x36/0x60
    # [    0.158399]  ? ct_nmi_enter+0x9c/0x190
    # [    0.158399]  kasan_report.cold+0x8/0xd
    # [    0.158399]  ? ct_nmi_enter+0x9c/0x190
    # [    0.158399]  kasan_check_range+0x35/0x1c0
    # [    0.158399]  ct_nmi_enter+0x9c/0x190
    # [    0.158399]  irqentry_enter+0x30/0x40
    # [    0.158399]  common_interrupt+0x15/0xc0
    # [    0.158399]  asm_common_interrupt+0x22/0x40
    # [    0.158399] RIP: 0010:get_cpu_cap+0xe0/0xc30
    # [    0.158399] Code: 14 02 4c 89 f8 83 e0 07 83 c0 03 38 d0 7c 08 84 d2 0f 85 dd 09 00 00 83 7d 24 05 0f 8e 1c 08 00 00 b8 06 00 00 00 31 c9 0f a2 <48> ba 00 00 00 00 00 fc ff df 48 8d 7d 60 48 89 f9 48 c1 e9 03 0f
    # [    0.158399] RSP: 0000:ffffffffb8007e50 EFLAGS: 00000246
    # [    0.158399] RAX: 0000000000000004 RBX: 0000000000000000 RCX: 0000000000000000
    # [    0.158399] RDX: 0000000000000000 RSI: 1ffffffff719a63b RDI: ffffffffb8cd31d8
    # [    0.158399] RBP: ffffffffb8cd31a0 R08: 0000000000000001 R09: 0000000000000000
    # [    0.158399] R10: ffffffffb8cd31a8 R11: 0000000000000001 R12: ffffffffb8cd3238
    # [    0.158399] R13: ffffffffb8cd31a0 R14: ffffffffb8cd31c8 R15: ffffffffb8cd31c4
    # [    0.158399]  ? get_cpu_vendor+0x8c/0x280
    # [    0.158399]  identify_cpu+0x35c/0x1d00
    # [    0.158399]  ? mutex_unlock+0x7b/0xd0
    # [    0.158399]  ? __mutex_unlock_slowpath.constprop.0+0x2a0/0x2a0
    # [    0.158399]  ? jump_label_update+0x11b/0x360
    # [    0.158399]  identify_boot_cpu+0xd/0xb5
    # [    0.158399]  arch_cpu_finalize_init+0x5/0xa1
    # [    0.158399]  start_kernel+0x314/0x3b7
    # [    0.158399]  secondary_startup_64_no_verify+0xe0/0xeb
    # [    0.158399]  </TASK>
    # virtme-run: failed to start virtiofsd, fallback to 9p
    re.compile(re.escape('BUG: KASAN: wild-memory-access in ct_nmi_enter')),

    # Traceback (most recent call last):
    #   File "/usr/bin/virtme-run", line 8, in <module>
    #     sys.exit(main())
    #   File "/usr/lib/python3/dist-packages/virtme/commands/run.py", line 1314, in main
    #     return do_it()
    #   File "/usr/lib/python3/dist-packages/virtme/commands/run.py", line 783, in do_it
    #     kernel = find_kernel_and_mods(arch, args)
    #   File "/usr/lib/python3/dist-packages/virtme/commands/run.py", line 486, in find_kernel_and_mods
    #     if not os.path.exists(virtme_mods) or is_file_more_recent(
    #   File "/usr/lib/python3/dist-packages/virtme/commands/run.py", line 307, in is_file_more_recent
    #     return os.stat(a).st_mtime > os.stat(b).st_mtime
    # FileNotFoundError: [Errno 2] No such file or directory: '/src/linux_kernel/.virtme_mods/lib/modules/0.0.0/modules.dep'
    # --
    # fix in upstream virtme-ng, apparently not present in Linux CP as of 7/7/24:
    # https://github.com/winnscode/virtme-ng/commit/c0eba04165003022ae3e7d8f0a3c01ccdb7639a9
    re.compile(r"No such file or directory: '.*\.virtme_mods/lib/modules/0\.0\.0/modules\.dep'"),
]


class BadReturnCode(Exception):
    pass


async def run(func, *args, stdin=None, timeout=3600, **kwargs):
    await LOGGER.adebug("%s %s %s", func, args, kwargs)
    proc = await asyncio.create_subprocess_exec(
        func,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE if stdin else None,
        **kwargs,
    )

    stdout, stderr = await asyncio.wait_for(
        proc.communicate(input=stdin.encode("utf8") if stdin else None),
        timeout=timeout,
    )

    return_code = proc.returncode

    # Program outputs may not be decodeable when POV blobs are passed to them
    await LOGGER.adebug("Process stdout: %s", stdout.decode("utf8", errors="ignore"))
    await LOGGER.adebug("Process stderr: %s", stderr.decode("utf8", errors="ignore"))

    return return_code, stdout, stderr


class DockerImageUsage(enum.Enum):
    PULL = 'pull'
    BUILD = 'build'
    ALREADY_BUILT = 'already_built'
    NONE = 'none'

    @classmethod
    def from_config(cls) -> DockerImageUsage:
        val = v.get('docker_image_usage')
        if isinstance(val, str):
            if val.lower() == 'pull':
                return cls.PULL
            elif val.lower() == 'build':
                return cls.BUILD
            elif val.lower() == 'already_built':
                return cls.ALREADY_BUILT

        return cls.NONE


class DockerVolArgsBehavior(enum.Enum):
    OVERWRITE = 'overwrite'
    APPEND = 'append'
    NONE = 'none'

    @classmethod
    def from_config(cls) -> DockerVolArgsBehavior:
        val = v.get('docker_vol_args_behavior')
        if isinstance(val, str):
            if val.lower() == 'overwrite':
                return cls.OVERWRITE
            elif val.lower() == 'append':
                return cls.APPEND

        return cls.NONE

    def get_mode(self) -> str | None:
        if self == DockerVolArgsBehavior.OVERWRITE:
            return 'w+'
        elif self == DockerVolArgsBehavior.APPEND:
            return 'a+'
        else:
            return None


class AbstractCPWorkspace:
    # ABC for anything that implements CPWorkspace's API. Just used for
    # type hints -- see CPWorkspace (below) for the API itself.
    pass


class CPWorkspace(AbstractCPWorkspace, contextlib.AbstractAsyncContextManager):
    def __init__(self, cp_name: str, auditor: Auditor):
        cp = CPRegistry.instance().get(cp_name)
        if cp is None:
            raise ValueError(f"cp_name {cp_name} does not exist")
        self.auditor = auditor
        self.cp = cp
        self.project_yaml: dict[str, Any]
        self.repo: None
        self.run_env: dict[str, str]
        self.src_repo: Repo | None
        self.workdir: Path

    def is_team_atlanta_jenkins_fork(self):
        return v.get_bool('team_atlanta_jenkins_fork') and self.cp.name == 'jenkins'

    @staticmethod
    def image_name_for_cp(cp_name: str, *, include_version: bool) -> bool:
        """Get the name of the Docker image associated with the specified CP"""
        cp = CPRegistry.instance().get(cp_name)
        if cp is None:
            raise ValueError(f'unknown challenge project: {cp_name}')
        image_name = cp.project_yaml["docker_image"]
        if include_version:
            return image_name
        else:
            return image_name.split(':')[0]

    @classmethod
    async def is_docker_ready(cls, cp_name: str) -> bool:
        """
        Check if Docker has pulled the image needed to run commands for
        the specified CP
        """
        image_name = cls.image_name_for_cp(cp_name, include_version=False)

        # We use a flag to mark when Docker is ready, so we don't have
        # to keep running "docker images" over and over after we've
        # already seen it's ready
        image_name_for_flag = image_name.replace('/', '_')
        if await test_and_set(f"docker_ready_for_{image_name_for_flag}", None):
            return True

        return_code, stdout, stderr = await run("docker", "images")

        if image_name.encode("utf-8") in stdout:
            await test_and_set(f"docker_ready_for_{image_name_for_flag}", True)
            return True
        else:
            return False

    @classmethod
    async def await_docker_ready(cls, cp_name: str) -> None:
        """
        Wait until Docker has pulled the image needed to run commands
        for the specified CP
        """
        docker_image_usage = DockerImageUsage.from_config()
        if docker_image_usage in {DockerImageUsage.PULL, DockerImageUsage.BUILD}:
            # In these modes, we create or obtain our own Docker images,
            # so waiting for them here would never finish
            return

        image_name = None

        while True:
            if await cls.is_docker_ready(cp_name):
                break

            if not image_name:
                image_name = cls.image_name_for_cp(cp_name, include_version=False)
            await LOGGER.ainfo(
                'Docker does not appear to have image "%s" for CP "%s" ready yet -- waiting...',
                image_name, cp_name,
            )

            await asyncio.sleep(DOCKER_READY_CHECK_INTERVAL)

    async def __aenter__(self):
        # Make working copies
        self.project_yaml = self.cp.project_yaml

        self.repo = None  # not needed for VAPI
        # self.src_repo: Repo | None = None  # is a property in VAPI
        self.src_repo_name: str | None = None

        self.run_env = {
            "DOCKER_HOST": os.environ.get("DOCKER_HOST", ""),
        }

        extra_args = []
        internal_dir = self.workdir / ".internal_only"
        if internal_dir.is_dir():
            extra_args.append(f"-v {internal_dir}:/.internal_only")
        if self.is_team_atlanta_jenkins_fork():
            extra_args.append(f"-v {self.workdir}/work/maven_repo:/maven_repo")
        if extra_args:
            self.run_env["DOCKER_EXTRA_ARGS"] = " ".join(extra_args)

        await LOGGER.adebug("Workspace: setup")

        docker_image_usage = DockerImageUsage.from_config()

        if docker_image_usage == DockerImageUsage.BUILD:
            await run("make", "docker-build", cwd=self.workdir)
            await run("make", "docker-config-local", cwd=self.workdir)

            if self.is_team_atlanta_jenkins_fork():
                await run(
                    "./run.sh", "prebuild", cwd=self.workdir, env=self.run_env
                )

        elif docker_image_usage == DockerImageUsage.ALREADY_BUILT:
            await run("make", "docker-config-local", cwd=self.workdir)

        elif docker_image_usage == DockerImageUsage.PULL:
            if not os.environ.get("GITHUB_USER", "") or not os.environ.get("GITHUB_TOKEN", ""):
                raise RuntimeError(
                    'For "pull" DOCKER_IMAGE_USAGE, the GITHUB_USER and GITHUB_TOKEN environment variables are required.'
                    ' These are normally provided by the "env" file.'
                    " See the CAPI team-atlanta branch README.md for more information.")

            if self.is_team_atlanta_jenkins_fork():
                await LOGGER.awarning('The team-atlanta fork of Jenkins CP does not support pulling Docker image packages, but trying anyway...')

            img_name = self.project_yaml["docker_image"]
            self.run_env.update({"DOCKER_IMAGE_NAME": img_name})

            await run(
                "docker",
                "login",
                "ghcr.io",
                "-u",
                os.environ.get("GITHUB_USER", ""),
                "--password-stdin",
                stdin=os.environ.get("GITHUB_TOKEN", ""),
            )
            await run("docker", "pull", img_name)

        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        # Removed because VAPI shouldn't delete workdirs:

        # shutil.rmtree(self.workdir, ignore_errors=True)

        pass

    def set_src_repo(self, ref: str):
        raise NotImplementedError('removed from VAPI')

    def set_src_repo_by_name(self, source: str):
        self.src_repo_name = source

    @property
    def src_repo(self) -> Repo | None:
        if self.src_repo_name is None:
            return None
        return Repo(self.workdir / "src" / self.src_repo_name)

    def sanitizer(self, sanitizer_id: str) -> str | None:
        return self.project_yaml.get("sanitizers", {}).get(sanitizer_id)

    def harness(self, harness_id: str) -> str | None:
        return self.project_yaml.get("harnesses", {}).get(harness_id, {}).get("name")

    def current_commit(self) -> str | None:
        if self.src_repo is None:
            return None
        return self.src_repo.head.commit.hexsha.lower()

    def commit_list(self, source: str) -> list[str]:
        """
        In chronological order, oldest to newest, up to the head ref.
        """
        ref = self.cp.head_ref_from_source(source)
        repo = Repo(self.cp.root_dir / "src" / source)
        return list(reversed([commit.hexsha.lower() for commit in repo.iter_commits(ref)]))

    async def checkout(self, ref: str):
        LOGGER.debug("Workspace: checkout %s", ref)

        if self.src_repo is None:
            raise NotImplementedError

        # Workaround for a Git bug: if we don't run this command, Git
        # will check out every single file, updating all the
        # modification times and breaking incremental builds.
        # https://www.reddit.com/r/git/comments/c5c6ky/comment/es1on6x/
        await run(
            "git", "update-index", "--refresh", cwd=self.src_repo.working_dir,
        )

        self.src_repo.git.checkout(ref, force=True)

        LOGGER.debug("Checked out %s", self.current_commit())

    async def build(self, source: str | None, patch_sha256: str | None = None) -> bool:
        await LOGGER.adebug(
            "Workspace: build" + (f" with patch {patch_sha256}" if patch_sha256 else "")
        )

        docker_vol_args_mode = DockerVolArgsBehavior.from_config().get_mode()

        if docker_vol_args_mode is not None:
            docker_vol_args = [
                f"-v {self.workdir}/work:/work",
                f"-v {self.workdir}/src:/src",
                f"-v {self.workdir}/out:/out",
            ]
            # In my testing, specifying the .internal_only volume twice
            # (via both DOCKER_EXTRA_ARGS and here) doesn't actually
            # cause a problem, but it does make me a bit nervous anyway,
            # so let's avoid it
            if '.internal_only' not in self.run_env.get('DOCKER_EXTRA_ARGS', ''):
                docker_vol_args.append(f"-v {self.workdir}/.internal_only:/.internal_only")

            with open(self.workdir / ".env.project", docker_vol_args_mode, encoding="utf8") as env:
                env.write(
                    f'\nDOCKER_VOL_ARGS="{" ".join(docker_vol_args)}"\n'
                )

        try:
            if patch_sha256 is None:
                return_code, _, _ = await run(
                    "./run.sh",
                    "-x",
                    "-v",
                    "build",
                    cwd=self.workdir,
                    env=self.run_env,
                    timeout=1200,
                )

            else:
                if source is None:
                    raise ValueError('source must be specified when building with patch')

                patch = Flatfile(contents_hash=patch_sha256)
                return_code, _, _ = await run(
                    "./run.sh",
                    "-x",
                    "-v",
                    "build",
                    patch.filename,
                    source,
                    cwd=self.workdir,
                    env=self.run_env,
                    timeout=1200,
                )

            return return_code == 0
        except TimeoutError:
            await self.auditor.emit(EventType.TIMEOUT, context=TimeoutContext.BUILD)
            return False

    async def check_sanitizers(self, blob_sha256: str, harness: str) -> set[str]:
        blob = Flatfile(contents_hash=blob_sha256)
        await LOGGER.adebug(
            "Workspace: check sanitizers on harness %s with blob (hash %s)",
            harness,
            blob.sha256,
        )

        all_return_codes = 0
        all_timed_out = True
        for i in range(SPURIOUS_FAILURE_ATTEMPTS):
            if i > 0:
                await LOGGER.awarning(
                    "Spurious PoV failure detected -- retrying (%d/%d)",
                    i + 1, SPURIOUS_FAILURE_ATTEMPTS,
                )

            try:
                return_code, _, _ = await run(
                    "./run.sh",
                    "-x",
                    "-v",
                    "run_pov",
                    blob.filename,
                    self.harness(harness),
                    cwd=self.workdir,
                    env=self.run_env,
                    timeout=600,
                )
                all_return_codes |= return_code
            except TimeoutError:
                await self.auditor.emit(
                    EventType.TIMEOUT, context=TimeoutContext.CHECK_SANITIZERS
                )
                retry = True
                continue

            all_timed_out = False

            output_dir = self.workdir / "out" / "output"

            pov_output_path = [
                p
                for p in sorted(os.listdir(output_dir), reverse=True)
                if p.endswith("run_pov")
            ][0]

            retry = False
            triggered: set[str] = set()
            for file in [
                output_dir / pov_output_path / "stderr.log",
                output_dir / pov_output_path / "stdout.log",
            ]:
                try:
                    with open(file, "r", encoding="utf8") as f:
                        contents = f.read()
                        for key, sanitizer in self.project_yaml["sanitizers"].items():
                            if sanitizer in contents:
                                triggered.add(key)
                        if any(r.search(contents) for r in SPURIOUS_FAILURE_INDICATORS):
                            retry = True
                except FileNotFoundError:
                    await LOGGER.awarning("%s not found", file)

            if retry:
                continue
            elif return_code == 0:
                return triggered
            else:
                raise BadReturnCode

        if all_return_codes != 0 or all_timed_out:
            raise BadReturnCode
        else:
            # TODO: may be useful to be able to indicate failure here (None return value?)
            await LOGGER.awarning(
                "Failed to successfully run PoV after %d attempts -- giving up",
                SPURIOUS_FAILURE_ATTEMPTS,
            )
            return set()

    async def run_functional_tests(self) -> bool:
        await LOGGER.adebug("Workspace: run tests")
        try:
            return_code, _, _ = await run(
                "./run.sh",
                "-x",
                "-v",
                "run_tests",
                cwd=self.workdir,
                env=self.run_env,
                timeout=600,
            )
            return return_code == 0
        except TimeoutError:
            await self.auditor.emit(
                EventType.TIMEOUT, context=TimeoutContext.RUN_FUNCTIONAL_TESTS
            )
            return False
