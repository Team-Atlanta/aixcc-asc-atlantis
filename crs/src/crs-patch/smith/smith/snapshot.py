import logging
import traceback

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING, Optional
from pathlib import Path
from typing_extensions import override

from .runner import TestResult
from .utils import rsync_dir, rsync_file

if TYPE_CHECKING:
    from .challenge import Challenge

logger = logging.getLogger(__name__)

class Snapshot(ABC):
    def __init__(self, challenge: "Challenge"):
        self._challenge = challenge
        self.get_snapshot_dir().mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def name(self) -> str:
        pass

    def get_snapshot_dir(self) -> Path:
        return self._challenge.cache_dir / "snapshots" / self.name()

    def _get_logs_dir(self) -> Path:
        return self._challenge.cache_dir / "logs" / self.name()

    # Cache the result of the snapshot to avoid rebuilding the challenge
    def _get_save_result_path(self) -> Path:
        return self._get_logs_dir() / '.save_result'

    def _get_save_result(self) -> Optional[bool]:
        result_file = self._get_save_result_path()
        if not result_file.exists():
            return None
        return result_file.read_text() == '1'

    def _set_save_result(self, result: bool):
        result_file = self._get_save_result_path()
        result_file.write_text('1' if result else '0')

    def load(self) -> bool:
        if not self._get_save_result():
            return False

        if not rsync_dir(self.get_snapshot_dir(), self._challenge.root_dir):
            return False

        if self._challenge.root_dir != self._challenge.build_root_dir and \
            not rsync_dir(self.get_snapshot_dir(), self._challenge.build_root_dir):
            # rsync build_root_dir too only if it is different from root_dir
            return False

        return True

    def save(self) -> Optional[bool]:
        """
        returns True if it newly saved the snapshot,
        False if the snapshot was already saved,
        None if the snapshot was failed to save
        """
        res = self._get_save_result()
        if res is not None:
            return False

        res = self._save_impl()
        self._set_save_result(res)
        return True if res else None

    def _save_impl(self) -> bool:
        if not self._patch():
            logger.warning("Failed to patch the snapshot")
            return False

        if not self._build():
            logger.warning("Failed to build the snapshot")
            return False

        if not self._import():
            logger.warning("Failed to import the snapshot")
            return False
        return True

    def _import(self) -> bool:
        return rsync_dir(self._challenge.build_root_dir, self.get_snapshot_dir())

    def _build(self) -> bool:
        # Disable this as we will build the challenge in the debug snapshot
        output_dir = self._get_logs_dir() / 'build'
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            (ok, msg) = self._challenge.perform_build(output_dir)
            assert ok == TestResult.OK, msg
        except Exception as e:      # pylint: disable=broad-except
            logger.debug(f"Failed to prepare the challenge: {e}")
            traceback.print_exc()
            return False
        return True

    def _import_file(self, rel_path: Path) -> bool:
        src = self._challenge.build_root_dir / rel_path
        dst = self.get_snapshot_dir() / rel_path
        if not dst.parent.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
        return rsync_file(src, dst)

    def _export_file(self, rel_path: Path) -> bool:
        src = self.get_snapshot_dir() / rel_path
        dst = self._challenge.build_root_dir / rel_path
        return rsync_file(src, dst)

    def _patch(self) -> bool:
        return True


class SnapshotManager(ABC):
    def __init__(self, challenge: "Challenge", snapshots: List[Snapshot]):
        self._challenge = challenge
        self._clean = CleanSnapshot(self._challenge)
        self._snapshots = snapshots

        self._save_all()

    def reset(self) -> None:
        self._clean.load()

    def _save_all(self) -> None:
        assert self._clean.save() is not None

        for snapshot in self._snapshots:
            if snapshot.save() is True:
                # If the snapshot was newly saved, reset the challenge
                self.reset()

    def load(self) -> None:
        work_dir = self._challenge.cache_dir / 'work'
        self._challenge.set_root_dir(work_dir)

        snapshots = self._snapshots + [self._clean]
        for snapshot in snapshots:
            if snapshot.load():
                return

        raise ValueError("No snapshot loaded")

class CleanSnapshot(Snapshot):
    @override
    def name(self) -> str:
        return 'clean'

class DebugSnapshot(Snapshot):
    @override
    def name(self) -> str:
        return 'debug'

class CDebugSnapshot(DebugSnapshot):
    pass

class AIxCCUserlandCDebugSnapshot(DebugSnapshot):
    @override
    def _patch(self) -> bool:
        rel_path = Path('.env.docker')
        if not self._import_file(rel_path):
            return False

        docker_env_file = self.get_snapshot_dir() / rel_path
        original_env = docker_env_file.read_text()

        debug_flags = 'CP_HARNESS_EXTRA_CFLAGS=-g \n'
        if debug_flags not in original_env:
            docker_env_file.write_text(original_env + '\n' + debug_flags)

        return self._export_file(rel_path)


class AIxCCJenkinsDebugSnapshot(DebugSnapshot):
    @override
    def _patch(self) -> bool:
        # TODO: Implement this
        return True


class AIxCCLinuxDebugSnapshot(DebugSnapshot):
    @override
    def _patch(self) -> bool:
        rel_path = self._challenge.src_rel_dir / '.config'
        if not self._import_file(rel_path):
            return False

        # Fix .config to enable CONFIG_DEBUG_INFO and CONFIG_DEBUG_INFO_DWARF4.
        config_path = self.get_snapshot_dir() / rel_path
        old_config = config_path.read_text()
        new_config = []
        for line in old_config.split('\n'):
            if 'CONFIG_DEBUG_INFO' in line:
                continue
            new_config.append(line)

        new_config += ['CONFIG_DEBUG_INFO=y', 'CONFIG_DEBUG_INFO_DWARF4=y']
        config_path.write_text('\n'.join(new_config))
        return self._export_file(rel_path)
