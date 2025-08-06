"""
FuzzingManager class is responsible for managing the fuzzing process.
1. Turn off fuzzers if they do not extend coverage after a certain number of iterations.
2. Sync new corpus to the fuzzers.
3. Reload corpus if possible.
"""

import asyncio
from collections import defaultdict
import logging
from multiprocessing import Lock
from pathlib import Path
import re
from .singleton import Singleton
from .harness import AsyncFileReader, Harness
from .asynctask import AsyncTask
from .povmanager import PoVManager, ReportStatus, handle_line
from .utils import empty_function, run_cmd
from .config import SharedFile
import os
import json
import random

def copy(fr, to):
    if not fr.exists(): return
    if fr.is_dir(): run_cmd(["rsync", "-a", str(fr) + "/.", to])
    else: run_cmd(["rsync", "-a", fr, to])

class FuzzingManager(AsyncTask, metaclass=Singleton):
    def __init__(self, crs: Path, builddir: Path):
        self.crs = crs
        self.builddir = builddir
        self.harnesses: list[Harness]= []
        self.harness_ids: set[str] = set()
        # {harnesss_uid: True, ...}
        self.add_error_lines: dict[int, bool] = defaultdict(bool)
        # {harness_uid: [line, ...], ...}
        self.error_lines: dict[int, list[str]] = defaultdict(list)
        # {harness_uid: True, ...}
        self.need_report_error: dict[int, bool] = defaultdict(bool)
        # {harness_id: [Path, ...], ...}
        self.corpus: dict[str, set[str]] = defaultdict(set)
        self.corpus_lock = Lock()
        # {harness_id, ...}
        self.reported: dict[str, int] = {}
        super().__init__()
        self.LOG = self.logging_init("fuzzing-manager-check")
    
    def get_shared_path(self, path: Path, harness_id):
        crs_scratch = Path(os.environ.get("AIXCC_CRS_SCRATCH_SPACE", str(self.builddir.parent)))
        shared_dir = crs_scratch / ("shared_corpus/" + harness_id)
        os.makedirs(shared_dir, exist_ok = True)
        return shared_dir / path.name

    def to_shared_file(self, harness_id, src: str):
        src = Path(src)
        dst = self.get_shared_path(src, harness_id)
        copy(src, dst)
        d = SharedFile(dst).finalize()
        return d

    async def from_shared_folder(self, harness_id) -> tuple[str, list[str]]:
        # src = self.get_shared_path(dst)
        crs_scratch = Path(os.environ.get("AIXCC_CRS_SCRATCH_SPACE", str(self.builddir.parent)))
        shared_dir = crs_scratch / ("shared_corpus/" + harness_id)
        ret = []

        if not shared_dir.exists() or not shared_dir.is_dir() or not shared_dir.iterdir():
            return (harness_id, ret)

        for src in shared_dir.iterdir():
            if src.name.startswith(".meta_"): continue
            ret.append(str(src))

        return (harness_id, ret)

    def register_harnesses(self, harnesses):
        self.harnesses.extend(harnesses)
        self.harness_ids.update([harness.id for harness in harnesses])

    def kill_fuzzers(self):
        # TODO: kill fuzzers if they do not extend coverage after a certain number of iterations
        pass


    def add_corpus(self, harness_id, corpus: str):
        self.LOG.debug(f"Adding corpus for {harness_id}: {corpus}")
        if harness_id not in self.harness_ids:
            self.LOG.debug(f"Unknown harness_id: {harness_id}")
            self.to_shared_file(harness_id, corpus)
        else:
            with self.corpus_lock:
                self.corpus[harness_id].add(corpus)

    async def add_corpus_from_llm(self):

        async def _add_corpus_from_llm(self: FuzzingManager):
            tasks = [self.from_shared_folder(h_id) for h_id in self.harness_ids]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED, timeout=5)

            for task in done:
                harness_id, corpora = task.result()
                self.LOG.debug(f"Adding corpus for {harness_id}: {len(corpora)}")
                with self.corpus_lock:
                    self.corpus[harness_id].update(corpora)
        it = 0
        while it < 300:
            await _add_corpus_from_llm(self)
            self.sync_corpus()
            await asyncio.sleep(5)
            it += 1
    

    def sync_corpus(self):
        dict_res = {}
        with self.corpus_lock:
            for harness in self.harnesses:
                res = []
                corpora: set[str] = self.corpus[harness.id]
                if len(corpora) > 0:
                    self.LOG.debug(f"Syncing corpus for {harness.class_name} ({harness.id}): {len(corpora)}")
                    if dict_res.get(harness.id) == None:
                        dict_res[harness.id] = True

                for corpus in corpora:
                    res.append(harness.sync_corpus(corpus))

                dict_res[harness.id] = dict_res.get(harness.id, False) & all(res)

            self.LOG.debug(f"dict_res: {dict_res}")
            for harness_id, res in dict_res.items():
                if res:
                    self.LOG.debug(f"Every corpus synced for ({harness_id})")
                    self.corpus[harness_id] = set()
    
    def copy_corpus_for_patching(self, harness: Harness, LOG):
        fuzz_dir = harness.harness_dir / "fuzz" / harness.class_name
        corpus_dir = fuzz_dir / "corpus_dir"

        
        if not corpus_dir.exists():
            return

        dst_dir = os.environ.get("AIXCC_CRS_SCRATCH_SPACE", str(self.builddir.parent.parent)) + "/corpus/" + harness.id
        priority_json = os.environ.get("AIXCC_CRS_SCRATCH_SPACE", str(self.builddir.parent.parent)) + "/corpus/" + harness.id + ".json"

        os.makedirs(dst_dir, exist_ok = True)
        copy(corpus_dir, dst_dir)

        files = list(corpus_dir.iterdir())
        files.sort(key=lambda x: x.stat().st_ctime)

        priorities = {file.name: priority for priority, file in enumerate(files, start=1)}

        with open(priority_json, "w") as f:
            f.write(json.dumps(priorities))


    async def report_error(self, harness:Harness, error_logs: str, LOG: logging.Logger):
        pov_manager = PoVManager(self.crs)

        # print_msg = error_logs.split("\n")[-14:]

        sanitizer_id = harness.cp.get_sanitizer_id(error_logs)

        if sanitizer_id == None:
            # self.LOG.info(f"report_error triggered. but sanitizer_id is None")
            # self.LOG.info(error_logs)
            return

        if sanitizer_id:
            san_msg = harness.cp.get_sanitizer_msg(sanitizer_id)
            m = re.search(r"Test unit written to (?P<blob_path>\/[^\s]+)", error_logs)
            if m:
                blob_path = m.group("blob_path")
                new_blob_path = harness.transform_blob(blob_path)
                LOG.info(f"{san_msg}: {harness.class_name}({harness.id}), {harness.mode}")
                LOG.debug(f"new Blob path: {new_blob_path}")
                callback = empty_function
                res = await pov_manager.report(harness.id, new_blob_path, harness.cp, callback)

                if res != ReportStatus.ACCEPT:
                    LOG.error(f"PoV isn't confirmed ({res}): {harness.id}, {sanitizer_id}")
                    LOG.error(f"   - {new_blob_path}")
                else:
                    if harness.id not in self.reported:
                        self.reported[harness.id] = 1
                        self.copy_corpus_for_patching(harness, LOG)
                    else:
                        self.reported[harness.id] += 1
                        if random.random() < 1 / self.reported[harness.id]:
                            self.copy_corpus_for_patching(harness, LOG)


            else:
                LOG.info("No blob path found; Something went wrong")

    async def handle_lines(self, harness: Harness, file_reader: AsyncFileReader):
        LOG = logging.getLogger(harness.class_name)
        lines = await harness.get_lines(file_reader)
        for line in lines:
            add_error_lines = self.add_error_lines[harness.uid]
            error_lines = self.error_lines[harness.uid]
            ret = handle_line(line, add_error_lines, error_lines)
            self.add_error_lines[harness.uid] = ret[0]
            self.error_lines[harness.uid] = ret[1]
            self.need_report_error[harness.uid] = ret[2]
            LOG.debug(line)

            if self.need_report_error[harness.uid]:
                error_logs = "\n".join(self.error_lines[harness.uid])
                self.need_report_error[harness.uid] = False
                self.error_lines[harness.uid] = []
                await self.report_error(harness, error_logs, LOG)


    async def check_harnesses(self, file_reader: AsyncFileReader):
        tasks = [self.handle_lines(harness, file_reader) for harness in self.harnesses]
        task = asyncio.gather(*tasks, return_exceptions=True)

        await task

        

    async def check(self):
        # Main loop for fuzzing manager
        file_reader = AsyncFileReader()
        self.LOG.info("Fuzzing Manager started")

        while True:
            await self.check_harnesses(file_reader)
            await asyncio.sleep(1)

