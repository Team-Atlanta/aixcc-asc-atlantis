import json
import multiprocessing
import os
from pathlib import Path
import sys
import time
import asyncio

from .singleton import Singleton
from .settings import DEV
from .logfactory import LOG

NODE_TYPE = "CP_JAVA_CRS_TYPE"
NODE_CNT = "CP_JAVA_CRS_CNT"
MAIN_NODE = "MAIN" # "WORKER_1", "WORKER_2"

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
        LOG.info(f"Wait SharedFile: {self.path}")
        path = self.__metadata()
        while not path.exists():
            time.sleep(1)

    async def async_wait(self):
        LOG.info(f"Wait SharedFile: {self.path}")
        path = self.__metadata()
        while not path.exists():
            await asyncio.sleep(1)

    def __str__(self): return self.path.__str__()

def get_env(key):
    value = os.environ.get(key)
    if value == None:
        LOG.error(f"env[{key}] is None")
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

class Config(metaclass=Singleton):
    paths = ["workdir", "builddir"]
    # workdir: a path to the working directory. It is used to store the output of the CRS and not shared with the host.
    # builddir: a path to the directory where the CRS stores the build artifacts including CP. It is shared with the host.
    def __init__ (self):
        self.workdir: Path = None
        self.builddir: Path = None
        self.total_fuzzing_time = 3600 * 4
        if DEV:
            self.entire_running_time = 3600 * 4
        else:
            self.entire_running_time = 3600 * 4
        core_num = multiprocessing.cpu_count()
        if core_num > 64:
            core_num = 64
        self.thread_num = core_num - 3
        self.retry_harness_gen = 5
        self.llm_poc_timeout = 60 * 60 # 1 hour
        self.commit_analyzer_timeout = 60 * 15 # 15 minutes
        self.left_core = self.thread_num
        self.num_test_harnesses = 1
    
    def set_num_test_harnesses(self, num_test_harnesses):
        self.num_test_harnesses = num_test_harnesses
    
    def set_left_core(self, left_core):
        self.left_core = left_core

    def load (self, fname):
        if not os.path.exists(fname): return
        with open(fname) as f: config = json.load(f)
        for key in vars(self):
            if key in config:
                if key in self.paths:
                    path = Path(os.path.expandvars(config[key]))
                    setattr(self, key, path)
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    setattr(self, key, config[key])
    def is_main(self):
        return get_env(NODE_TYPE) == MAIN_NODE

    def is_worker(self): return not self.is_main()

    def get_node_name(self): return get_env(NODE_TYPE)

    def __save_conf(self, build_dir, idx, data):
        path = build_dir / f"WORKER_{idx}.config"
        SharedFile(path).write(bytes(json.dumps(data), "utf-8"))

    def distribute_job(self, V):
        # LOG.info("Distribute jobs")
        node_cnt = int(get_env(NODE_CNT))
        if node_cnt == 1: return
        harnesses = list(V)
        jobs = distribute(harnesses, node_cnt)
        return jobs