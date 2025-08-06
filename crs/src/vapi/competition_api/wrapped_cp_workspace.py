import asyncio
import contextlib
import enum
import json
import os
from pathlib import Path
import random
import shutil
import string
import subprocess
from typing import Iterator

from structlog.stdlib import get_logger
from vyper import v

from competition_api.cp_workspace import AbstractCPWorkspace, CPWorkspace
from competition_api.file_folder_copy import copy_folder
from competition_api.sadlock import create_async_sadlock

v.set_default("artifact_cache_dir", f"{os.environ['AIXCC_CRS_SCRATCH_SPACE']}/vapi_artifact_cache")
LOGGER = get_logger(__name__)


class BuildStatus(enum.Enum):
    NOT_BUILT = 'not_built'
    BUILT_SUCCESS = 'built_success'
    BUILT_FAILURE = 'built_failure'
    CURRENTLY_BUILDING = 'currently_building'


def delta_sequence(limit: int) -> Iterator[int]:
    """0, -1, 1, -2, 2, -3, 3, ... (OEIS A130472)"""
    if limit <= 0: return

    i = 0
    yield i
    limit -= 1
    if limit == 0: return

    while True:
        i += 1

        yield -i
        limit -= 1
        if limit == 0: return

        yield i
        limit -= 1
        if limit == 0: return

assert [a for a in delta_sequence(5)] == [0, -1, 1, -2, 2]


def tag() -> str:
    """short random alphanumeric string"""
    s = ''
    for _ in range(8):
        s += random.choice(string.ascii_letters + string.digits)
    return s


class WrappedCPWorkspace(AbstractCPWorkspace):
    """
    Wrapper over CPWorkspace that adds the following features for VAPI:
    - Locking to prevent problems from concurrent CP builds
    - Caching for built artifacts
    - Caching for PoV test results
    - Logging of high-level events (build, PoV test, etc)
    """
    def __init__(self, *args, **kwargs):
        self.workspace: CPWorkspace | None = None
        self.workspace_args = args
        self.workspace_kwargs = kwargs

        master_cache_dir = Path(v.get("artifact_cache_dir"))
        master_cache_dir.mkdir(exist_ok=True)

        # note: ./run.sh doesn't work correctly from paths with spaces
        cp_name = args[0]
        self.cache_dir: Path = master_cache_dir / cp_name.replace(' ', '_')
        self.cache_dir.mkdir(exist_ok=True)

    @staticmethod
    async def await_docker_ready(cp_name: str) -> None:
        await CPWorkspace.await_docker_ready(cp_name)

    async def __aenter__(self):
        async with create_async_sadlock('setup'):
            self.workspace = CPWorkspace(*self.workspace_args, **self.workspace_kwargs)

            # DO NOT CHANGE: this cache key is expected by CRS-cp-linux when
            # providing us pre-built artifacts
            if self.have_cache_key('head'):
                await self.wait_until_cache_key_ready('head')
                self.switch_to_existing_cache_dir('head')
            else:
                self.switch_to_new_cache_dir('head', None)

            await self.workspace.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.workspace.__aexit__(exc_type, exc, tb)
        self.workspace = None

    def cache_dir_from_key(self, key: str) -> Path:
        return self.cache_dir / key

    def cache_json_path_from_key(self, key: str) -> Path:
        return Path(str(self.cache_dir_from_key(key)) + '.json')

    def have_cache_key(self, key: str) -> bool:
        return self.cache_dir_from_key(key).is_dir()

    def is_cache_key_ready(self, key: str) -> bool:
        # The JSON is only created after the folder-copy is completed,
        # so we use that to determine when the cache is ready for use
        return self.cache_json_path_from_key(key).is_file()

    async def wait_until_cache_key_ready(self, key: str) -> None:
        while not self.is_cache_key_ready(key):
            await asyncio.sleep(0.5)

    def delete_cache_key(self, key: str) -> None:
        shutil.rmtree(self.cache_dir_from_key(key), ignore_errors=True)
        self.cache_json_path_from_key(key).unlink(missing_ok=True)

    def current_cache_key(self) -> str:
        return self.workspace.workdir.name

    def switch_to_existing_cache_dir(self, key: str) -> None:
        self.workspace.workdir = self.cache_dir_from_key(key)

    def switch_to_new_cache_dir(self, key: str, base: str | None) -> None:
        if base is None:
            copy_src = self.workspace.cp.root_dir
        else:
            copy_src = self.cache_dir_from_key(base)

        copy_dst = self.cache_dir_from_key(key)
        LOGGER.debug(f'Initializing new cache directory {copy_dst} from {copy_src}')
        copy_folder(copy_src, copy_dst)

        # The existence of the JSON file is what signals that the cache
        # dir is ready for use (folder copy has been completed)
        self.cache_json_path_from_key(key).write_bytes(b'{}')

        self.switch_to_existing_cache_dir(key)

    def switch_to_temp_cache_dir(self) -> None:
        self.switch_to_new_cache_dir(f'temp-{tag()}', self.current_cache_key())

    @contextlib.asynccontextmanager
    async def current_cache_json_contents(self):
        """
        Read the contents of the current cache JSON file. Any changes to
        the object will be saved back to the file when the context is
        exited. If the file doesn't exist, it will be created.
        Takes a lock to ensure thread safety.
        """
        async with create_async_sadlock(self.current_cache_key()):
            json_path = self.cache_json_path_from_key(self.current_cache_key())
            if json_path.is_file():
                with json_path.open('r', encoding='utf-8') as f:
                    try:
                        json_data = json.load(f)
                    except json.decoder.JSONDecodeError:
                        json_data = {}
            else:
                json_data = {}

            yield json_data

            with json_path.open('w', encoding='utf-8') as f:
                json.dump(json_data, f)

    _linux_config_at_commit_cache = None
    def get_linux_config_at_commit(self, ref: str) -> bytes | None:
        """
        If the current CP is the Linux kernel, try to get the contents
        of the .config file at the specified commit
        """
        if self._linux_config_at_commit_cache is None:
            self._linux_config_at_commit_cache = {}

        if ref not in self._linux_config_at_commit_cache:
            self._linux_config_at_commit_cache[ref] = self._get_linux_config_at_commit(ref)

        return self._linux_config_at_commit_cache[ref]

    def _get_linux_config_at_commit(self, ref: str) -> bytes | None:
        if not self.workspace.cp.is_linux_kernel():
            return None

        source = self.workspace.cp.source_from_ref(ref)
        if source is None:
            return None

        try:
            return subprocess.check_output(
                ['git', 'show', f'{ref}:.config'],
                cwd=self.workspace.cp.root_dir / 'src' / source,
            )
        except Exception:
            return None

    def find_most_similar_built_cache_dir(self, key: str) -> str | None:
        """
        If the provided cache key is a commit ref, find the "most
        similar" (closest in the Git history) existing cache directory
        that has already been built successfully (not including the key
        itself)
        """
        if key == 'head':
            return None

        source = self.workspace.cp.source_from_ref(key)
        if source is None:
            return None

        commit_list = self.workspace.commit_list(source)

        this_commit_index = commit_list.index(key)
        this_linux_config = self.get_linux_config_at_commit(key)

        # First pass (Linux kernel CP only): we only consider commits
        # with a .config file that matches ours, as those are the only
        # commits that we can incrementally build from.
        # Second pass: we consider all commits.

        for require_matching_config in [True, False]:
            if require_matching_config and not self.workspace.cp.is_linux_kernel():
                continue

            for delta in delta_sequence(len(commit_list) * 4):
                if delta == 0: continue
                other_commit_idx = this_commit_index + delta
                if not (0 <= other_commit_idx < len(commit_list)): continue
                other_commit = commit_list[other_commit_idx]

                if require_matching_config:
                    if this_linux_config != self.get_linux_config_at_commit(other_commit):
                        continue

                if other_commit_idx == len(commit_list) - 1:
                    other_key = 'head'
                else:
                    other_key = other_commit

                if self.commit_build_status(other_commit) == BuildStatus.BUILT_SUCCESS:
                    return other_key

        return None

    # New API functions considered public:

    def clean_up(self) -> None:
        if self.current_cache_key().startswith('temp-'):
            self.delete_cache_key(self.current_cache_key())

    def commit_build_status(self, ref: str) -> BuildStatus:
        """
        Check whether the indicated commit has already been built, or is
        currently being built.
        `ref` can be a 40-char SHA-1 hash, or the string "HEAD".
        """
        ref = ref.lower()

        # Normalize to "head"
        source = self.workspace.cp.source_from_ref(ref)
        if source is not None and ref == self.workspace.cp.head_ref_from_source(source):
            ref = 'head'

        # Avoid using current_cache_json_contents() (or a hypothetical
        # similar function that lets you specify a different key),
        # because we don't want to update the file or block on a lock at
        # all, we only want to quickly check the current status of that
        # build
        json_path = self.cache_json_path_from_key(ref)
        if json_path.is_file():
            with json_path.open('r', encoding='utf-8') as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    # probably race condition...?
                    return BuildStatus.CURRENTLY_BUILDING

            if 'build_succeeded' in json_data:
                if json_data['build_succeeded']:
                    return BuildStatus.BUILT_SUCCESS
                else:
                    return BuildStatus.BUILT_FAILURE
            else:
                return BuildStatus.CURRENTLY_BUILDING
        else:
            return BuildStatus.NOT_BUILT

    # The remaining methods implement CPWorkspace's public API

    @property
    def cp(self):
        return self.workspace.cp
    @cp.setter
    def cp(self, value):
        self.workspace.cp = value

    @property
    def repo(self):
        return self.workspace.repo
    @repo.setter
    def repo(self, value):
        self.workspace.repo = value

    @property
    def src_repo(self):
        return self.workspace.src_repo
    @src_repo.setter
    def src_repo(self, value):
        self.workspace.src_repo = value

    def set_src_repo(self, ref: str):
        return self.workspace.set_src_repo(ref)

    def set_src_repo_by_name(self, source: str):
        LOGGER.debug(f'Setting source repo to {source}')
        return self.workspace.set_src_repo_by_name(source)

    def sanitizer(self, sanitizer_id: str) -> str | None:
        return self.workspace.sanitizer(sanitizer_id)

    def harness(self, harness_id: str) -> str | None:
        return self.workspace.harness(harness_id)

    def current_commit(self) -> str | None:
        return self.workspace.current_commit()

    def commit_list(self, source: str) -> list[str]:
        return self.workspace.commit_list(source)

    async def setup(self):
        return await self.workspace.setup()

    async def checkout(self, ref: str):
        async with create_async_sadlock('setup'):
            # DO NOT CHANGE: this cache key format is expected by
            # CRS-cp-linux when providing us pre-built artifacts
            new_cache_key = ref

            # If this is just HEAD, use that instead
            source = self.workspace.cp.source_from_ref(ref)
            if source is not None and ref == self.workspace.cp.head_ref_from_source(source):
                new_cache_key = 'head'

            if self.have_cache_key(new_cache_key):
                LOGGER.debug(f'Checking out {ref}: reusing cache dir')
                await self.wait_until_cache_key_ready(new_cache_key)
                self.switch_to_existing_cache_dir(new_cache_key)

            else:
                LOGGER.debug(f'Checking out {ref}: creating new cache dir')
                self.switch_to_new_cache_dir(
                    new_cache_key,
                    self.find_most_similar_built_cache_dir(new_cache_key) or 'head',
                )
                return await self.workspace.checkout(ref)

    async def build(self, source: str | None, patch_sha256: str | None = None) -> bool:
        if patch_sha256 is not None:
            await LOGGER.adebug("Building with patch")
            # Can't do any cache-related stuff when building with patch
            # -- in fact, we have to switch to a temp cache dir
            # specifically to avoid polluting a "real" cache dir
            async with create_async_sadlock('build'):
                self.switch_to_temp_cache_dir()
                return await self.workspace.build(source, patch_sha256=patch_sha256)

        else:
            async with self.current_cache_json_contents() as json_data:
                # If we have a cached result already, just return that
                if 'build_succeeded' in json_data:
                    res = json_data['build_succeeded']
                    await LOGGER.adebug(f"Build requested, but cached result available ({res}), so skipping build")
                    return res

                # Otherwise, get a lock and perform the build
                async with create_async_sadlock('build'):
                    await LOGGER.adebug("Building (no existing cache entry)")
                    res = await self.workspace.build(source)
                    json_data['build_succeeded'] = res
                    return res

    async def check_sanitizers(self, blob_sha256: str, harness: str) -> set[str]:
        async with self.current_cache_json_contents() as json_data:
            await LOGGER.adebug("Calling harness %s with POV blob", harness)

            pov_key = f'{blob_sha256}_{harness}'

            cached_res = json_data.get('sanitizers_cache', {}).get(pov_key)
            if cached_res is not None:
                await LOGGER.adebug(f"Sanitizers-check requested, but cached result available ({cached_res}), so just reusing that")
                return set(cached_res)

            res = await self.workspace.check_sanitizers(blob_sha256, harness)
            json_data.setdefault('sanitizers_cache', {})[pov_key] = list(res)
            return res

    async def run_functional_tests(self) -> bool:
        return await self.workspace.run_functional_tests()
