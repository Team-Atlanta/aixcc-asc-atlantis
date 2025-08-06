import os
import glob

from pathlib import Path

import git
import humanize

from loguru import logger

from .plugins import Workspace
from .util import walk_breadth_first
from .repomap import RepoMap

ROOT = Path(os.path.dirname(__file__))

DEFAULT_MAX_FILES = 1000
DEFAULT_IGNORE_DIRS = [".git", "node_modules", '__pycache__']
DEFAULT_IGNORE_FILES = [".pyc", ".pyo", ".o", ".DS_Store", ".class"]


class RepoWorkspace(Workspace):
    def __init__(self, repo, root=None, delete=True):
        super().__init__(root=root, delete=delete)

        # preparing CP
        self.copytree(repo, "repo")
        self.repo = self.get_path("repo")
        self.log(f"Loaded repo @{self.repo}", console=True)
        self.dict_dir = ROOT / "../dictionaries"

        if (self.repo / ".git").exists():
            logger.info(f"Open a git repo: {self.repo}")
            self.gitrepo = git.Repo(self.repo, odbt=git.GitDB)
        else:
            self.gitrepo = None

    def get_cwd(self):
        return self.workspace / "repo"

    def get_all_files(self, maxfiles=DEFAULT_MAX_FILES):
        files = []
        for pn in walk_breadth_first(self.repo, DEFAULT_IGNORE_DIRS, DEFAULT_IGNORE_FILES):
            if len(files) >= maxfiles:
                break
            files.append(Path(pn).relative_to(self.repo))
        return files

    def get_tracked_files(self, maxfiles=DEFAULT_MAX_FILES):
        if not self.gitrepo:
            return self.get_all_files(maxfiles)

        try:
            commit = self.gitrepo.head.commit
        except ValueError:
            commit = None

        files = []
        if commit:
            for blob in commit.tree.traverse():
                if blob.type == "blob":  # blob is a file
                    files.append(blob.path)

        # Add staged files
        index = self.gitrepo.index
        staged_files = [path for path, _ in index.entries.keys()]

        files.extend(staged_files)

        return list(set(self.normalize_path(path) for path in files))

    def normalize_path(self, path):
        # in case of a softlink-ed file, properly resolve as a unique path
        return (Path(self.repo) / path).relative_to(self.repo)

    def build_dictionaries(self):
        dirp = str(self.dict_dir / "*.dict")
        out = []
        for p in glob.glob(dirp):
            p = Path(p)
            sz = humanize.naturalsize(p.stat().st_size)
            out.append(f"{p.name} ({sz})")
        out = "\n".join(out)

        with open(self.history / "dicts.txt", "w") as fd:
            fd.write(out)

        return out

    def build_repomap(self, maxfiles=DEFAULT_MAX_FILES):
        self.repomap = self.get_repomap(maxfiles)
        with open(self.history / "repomap.txt", "w") as fd:
            fd.write(self.repomap)
        return self.repomap

    def get_repomap(self, maxfiles=DEFAULT_MAX_FILES):
        class DummyModel:
            def count_tokens(self, msg):
                return len(msg)

        files = self.get_tracked_files(maxfiles)

        repomap = RepoMap(main_model=DummyModel(), root=self.repo, cache_dir=self.tmp)
        return repomap.get_ranked_tags_map(set(), files)

    def read(self, pn):
        pn = self.root / pn
        if pn.exists():
            return pn.read_text()
        return ""

    def get_dict_path(self):
        return self.repo / "../out.dict"
