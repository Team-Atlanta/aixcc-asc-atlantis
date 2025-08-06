import contextlib
import glob
import itertools
import logging
import random
import re
import shutil
import socket
import time
import asyncio
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import threading
import aiofiles

from .cp import CP
from .logfactory import get_level
from .utils import empty_function, run_cmd
from .utils import run_cmd
from .asynctask import AsyncTask
from .config import Config

SWAT_PORT_START = 18000
SWAT_PORT_END = 19000

class AsyncFileReader:
    def __init__(self):
        self.file_positions = {}

    async def read_new_lines(self, file_path):
        if os.path.exists(file_path) == False:
            return []
        position = self.file_positions.get(file_path, 0)

        async with aiofiles.open(file_path, 'r') as f:
            await f.seek(position)
            lines = await f.readlines()
            self.file_positions[file_path] = await f.tell()

        if lines and not lines[-1].endswith('\n'):
            self.file_positions[file_path] -= len(lines[-1])
            lines = lines[:-1]

        return lines



class Harness(AsyncTask):
    def __init__(self, class_name: str, mode: str, cp: CP, harness_dir: Path, harness_id: str, source: Path, target_class_name, directed_fuzzing):
        self.uid = hash(self)
        self.id = harness_id
        self.cp = cp
        self.target_class_name = target_class_name
        self.harness_dir = harness_dir
        self.class_name = class_name
        self.mode = mode
        self.directed_fuzzing = directed_fuzzing
        self.source = source
        self.fuzzer = None
        self.fuzzer_cwd = None
        self.fuzzer_core = None
        self.buffer = ""
        super().__init__()
        self.LOG = self.logging_init(self.class_name)

    def filter_stderr(self, line: str):
        if line.startswith("+"):
            # Avoid printing shell commands
            return True
        elif line.startswith("INFO") or line.startswith("WARN"):
            # Avoid printing jazzer's complaints
            return True
        else:
            return False

    def remove(self):
        run_cmd(["rm", "-rf", self.class_name + "*"], cwd=self.harness_dir)

        # delete blob generator
        if self.mode == "proto":
            run_cmd(["rm", "-rf", self.target_class_name + "/_BlobGenerator.java"], cwd=self.harness_dir)
        elif self.mode == "jazzer":
            run_cmd(["rm", "-rf", self.target_class_name + "_JazzerBlobGenerator.java"], cwd=self.harness_dir)


    def deserialize_blob(self, blob_path: str):
        with open(blob_path, "rb") as f:
            blob = f.read()
            # Drop first 5 bytes
            if len(blob) >= 5:
                blob = blob[5:]

        new_blob_path = None

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(blob)
            new_blob_path = f.name

        return new_blob_path

    def serialize_blob(self, blob_path: str):
        with open(blob_path, "rb") as f:
            blob = f.read()
            # Drop first 5 bytes
            blob = struct.pack('B', 1) + struct.pack('>I', len(blob)) + blob

        new_blob_path = None

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(blob)
            new_blob_path = f.name

        return new_blob_path

    def transform_blob(self, blob_path: str):
        # "--experimental_mutator=1" serialized the blob content
        # This function deserializes the blob content to run `run.sh run_pov` command

        if self.mode == "proto":
            fuzz_dir = self.harness_dir / "fuzz" / self.class_name
            run_cmd(["bash", "proto_input_transform.sh"], cwd=fuzz_dir)

            s = blob_path.split("/")
            file_name = s[-1]
            dir_path = "/".join(s[:-2])

            new_blob_path = f"{dir_path}/artifacts/{file_name}"

            return new_blob_path
        elif self.mode == "jazzer":
            fuzz_dir = self.harness_dir / "fuzz" / self.class_name
            run_cmd(["bash", "jazzer_input_transform.sh"], cwd=fuzz_dir)

            s = blob_path.split("/")
            file_name = s[-1]
            dir_path = "/".join(s[:-2])

            new_blob_path = f"{dir_path}/artifacts/{file_name}"

            # return self.deserialize_blob(new_blob_path)
            return new_blob_path
        else:
            return self.deserialize_blob(blob_path)

    def run_dict_gen(self, workdir: str):
        self.LOG.info(f"Running dictionary generator for {self.class_name}")

        cmd = [workdir + "/run_dict_gen.sh", self.harness_dir, self.class_name, self.mode]

        run_cmd(cmd, cwd=self.cp.base)


    def sync_corpus(self, corpus: str):

        new_corpus_path = self.serialize_blob(corpus)

        fuzz_dir = self.harness_dir / "fuzz" / self.class_name

        if self.mode == "proto":
            corpus_dir = fuzz_dir / "corpus_dir_proto_format"
        elif self.mode == "jazzer":
            corpus_dir = fuzz_dir / "corpus_dir_jazzer_format"
        else:
            corpus_dir = fuzz_dir / "corpus_dir"

        if not corpus_dir.exists():
            # self.LOG.error(f"Corpus directory not found: {corpus_dir}")
            # It is possible if fuzzing is not started yet
            return False

        run_cmd(["cp", new_corpus_path, corpus_dir])
        return True


    async def get_lines(self, file_reader: AsyncFileReader):
            if not self.fuzzer:
                return []
        
        # def _read1_wrapper():
        #     try:
        #         return [self.fuzzer.stderr.read1()]
        #     except:
        #         return [b""]



        # else:
            # loop = asyncio.get_event_loop()
            # task = loop.run_in_executor(None, self.fuzzer.stderr.read1)
            task = asyncio.to_thread(self.fuzzer.stderr.read1)
            try:
                text = await asyncio.wait_for(task, 1)
            except asyncio.TimeoutError:
                text = b""

            try:
                text = text.decode("utf-8")
            except:
                text = ""

            self.buffer += text

            lines = []

            if "\n" in self.buffer:
                lines = self.buffer.split("\n")
                self.buffer = lines[-1]
                lines = lines[:-1]

            fuzz_dir = self.harness_dir / "fuzz" / self.class_name
            if self.mode == "jazzer" and len(lines) > 0 and fuzz_dir.exists():
                async with aiofiles.open(fuzz_dir / "stderr", "a") as f:
                    await f.write("\n".join(lines) + "\n")

            if self.mode == "naive" and self.fuzzer_core > 1: # run -jobs mode
                log_paths = [f'{self.fuzzer_cwd}/fuzz-{idx}.log' for idx in range(self.fuzzer_core)]
                tasks = [asyncio.create_task(file_reader.read_new_lines(f"{log_path}")) for log_path in log_paths]
                task = asyncio.gather(*tasks, return_exceptions=True)
                try:
                    texts = await asyncio.wait_for(task, 1)
                except asyncio.TimeoutError:
                    texts = []
                texts = list(itertools.chain.from_iterable(texts))
                texts = [t.strip() for t in texts]
                lines.extend(texts)

            return lines


    def compile(self, workdir: Path):
        self.LOG = self.logging_init(self.class_name)

        cmd = [workdir / "build_harness.sh",
            self.cp.base, self.harness_dir, self.class_name, self.mode, self.id]

        new_env = os.environ.copy()

        if self.directed_fuzzing:
            new_env["JAZZER_PATH"] = "/classpath/jazzer_directed"
        elif self.mode == "jazzer":
            new_env["JAZZER_PATH"] = "/classpath/jazzer_asc"
        else:
            new_env["JAZZER_PATH"] = "/classpath/jazzer"

        proc = run_cmd(cmd, cwd=self.cp.base, env = new_env)
        return proc.returncode == 0



    def run(self, workdir: Path, dict_gen: bool = False):

        # Run fuzzer
        new_env = os.environ.copy()

        repo_list = ':'.join((self.cp.base / "src" / r).resolve().as_posix() for r in self.cp.sources)

        directed_fuzzing_opt = "--disable_directed_fuzzing"

        stdout = subprocess.PIPE
        stderr = subprocess.PIPE


        self.LOG.info(f"Running jazzer for {self.class_name}")

        os.makedirs("/tmp/jazzer", exist_ok=True)

        core_per_harness = 1

        if self.directed_fuzzing:
            new_env["JAZZER_PATH"] = "/classpath/jazzer_directed"
            directed_fuzzing_opt = ""
        elif self.mode == "jazzer":
            new_env["JAZZER_PATH"] = "/classpath/jazzer_asc"
        else:
            new_env["JAZZER_PATH"] = "/classpath/jazzer"
            _core_per_harness = Config().left_core / Config().num_test_harnesses
            if _core_per_harness >= 1:
                core_per_harness = int(_core_per_harness) + 1
                self.fuzzer_core = core_per_harness

        cmd = [workdir / "run_fuzzer.sh",
            self.cp.base, self.harness_dir, self.class_name, self.mode,
            repo_list, self.id, str(core_per_harness), directed_fuzzing_opt]
        
        fuzzer_cwd = tempfile.mkdtemp()
        self.LOG.debug(f"Running fuzzer in {fuzzer_cwd}")

        proc = subprocess.Popen(cmd, cwd = fuzzer_cwd,
                                        stdout = stdout,
                                        stderr = stderr,
                                        env = new_env)

        self.fuzzer = proc
        self.fuzzer_cwd = fuzzer_cwd
        return


    def find_free_port(self):
        while True:
            port = random.randint(SWAT_PORT_START, SWAT_PORT_END)
            try:
                with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                    s.bind(('127.0.0.1', port))
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    return s.getsockname()[1]
            except:
                pass


    def run_concolic(self, workdir: Path, builddir: Path):
        print("Running concolically")
        self.LOG = self.logging_init(self.class_name)

        # Run concolic executor

        harness_build_path = self.harness_dir/self.class_name
        self.LOG.info(f"Harness_build_path: {harness_build_path}")

        swat_dir = (workdir)/'SWAT'
        swat_scripts_dir = swat_dir / 'scripts'

        # create fuzz paths
        concolic_fuzz_path = ((self.harness_dir / 'fuzz') / self.class_name)
        self.LOG.info(f"Concolic_fuzz_path: {concolic_fuzz_path}")

        if not os.path.exists(concolic_fuzz_path):
            os.makedirs(concolic_fuzz_path)
        else:
            # don't delete
            pass
            # delete everything on restart for test
            #os.system(f"rm -rf {concolic_fuzz_path}")
            #os.makedirs(concolic_fuzz_path)

        # make sure the directory has been created
        while not os.path.exists(concolic_fuzz_path):
            self.LOG.info("Waiting for concolic_fuzz_path {concolic_fuzz_path} to be up")
            time.sleep(3)

        # get the class paths
        new_env = os.environ.copy()
        cmd = [ swat_scripts_dir / "get_classpath_for_concolic_harness.sh" ]
        cmd += [self.cp.base, self.harness_dir, self.class_name, 'concolic', self.id]

        #print(' '.join([str(x) for x in cmd]))

        log_dir = f"{builddir}/logs"
        stdout_fn = f'{log_dir}/{self.class_name}.stdout'
        stderr_fn = f'{log_dir}/{self.class_name}.stderr'

        stdout = open(stdout_fn, "ab")
        self.stdout = subprocess.DEVNULL
        # For DEBUG
        #stderr = open(stderr_fn, "ab")
        self.stderr = subprocess.DEVNULL

        classpaths = f'{harness_build_path}:' + str(subprocess.check_output(cmd, cwd = workdir, env = new_env, stderr=self.stderr), 'utf-8').strip()
        #print(classpaths)

        sym_vars = 'Ljava/lang/String'
        http_port_to_use = str(self.find_free_port())
        #print(http_port_to_use)

        cmd = [ swat_scripts_dir / "run-swat.py" ]
        cmd += ['-s', swat_dir] # SWAT PATH

        cmd += ['-H', self.harness_dir,] # harness parent directory
        cmd += ['-c', self.class_name,] # harness class name
        cmd += ['-l', log_dir,]
        cmd += ['-p', classpaths]
        cmd += ['-v', sym_vars,]
        cmd += ['-t', http_port_to_use,]

        #self.LOG.info(' '.join([str(x) for x in cmd]))


        self.LOG.info(f"Running SWAT for {self.class_name} logdir {log_dir}")

        proc = subprocess.Popen(cmd, cwd = concolic_fuzz_path,
                                        stdout = self.stdout,
                                        stderr = self.stderr,
                                        env = new_env)

        self.fuzzer = proc
