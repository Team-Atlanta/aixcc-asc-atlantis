import asyncio
from functools import partial
import logging
from logging.handlers import QueueHandler, QueueListener
import multiprocessing
import os
from pathlib import Path
import socket
import subprocess
import time
import random
import subprocess
import tempfile
import threading
import psutil

from .logfactory import LOG
from .settings import DEV
from .cp import CP
from .harness_gen import HarnessGenerator
from .utils import run_cmd
from .harness import Harness
from .llm_poc_runner import LLMPoCRunner
from .povmanager import PoVManager
from .config import Config, SharedFile
from multiprocessing.pool import AsyncResult, ThreadPool
from .fuzzingmanager import FuzzingManager

def kill_process_tree(pid, include_parent=True):
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    children = parent.children(recursive=True)
    for child in children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass

    _, alive = psutil.wait_procs(children, timeout=5)
    for p in alive:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass

    if include_parent:
        try:
            parent.terminate()
        except psutil.NoSuchProcess:
            pass
        try:
            parent.wait(5)
        except psutil.NoSuchProcess:
            pass
        except psutil.TimeoutExpired:
            try:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
        
def is_port_listening(port, host="127.0.0.1"):
    cmd = "netstat -anpe".split()
    proc = run_cmd(cmd)
    stdout_lines = proc.stdout.split(b'\n')
    for line in stdout_lines:
        if (bytes(f':{port}', 'utf-8') in line) and \
            (b'LISTEN' in line):
            return True
    return False


def pool_init(q):
    # This is necessary to make the logging work in the pool
    # all records from worker processes go to qh and then into q
    qh = QueueHandler(q)
    root = logging.getLogger()
    root.addHandler(qh)


def pool_logger_init():
    q = multiprocessing.Queue()

    # ql gets records from the queue and sends them to the handler
    ql = QueueListener(q)
    ql.start()

    return ql, q


def run_joern_server():
    run_cmd(["run-joern.sh"])

def copy(fr, to):
    if not fr.exists(): return
    if fr.is_dir(): run_cmd(["rsync", "-a", str(fr) + "/.", to])
    else: run_cmd(["rsync", "-a", fr, to])


class Runner:
    def __init__ (self, cp: CP, workdir: Path, builddir: Path):
        self.workdir: Path = workdir
        self.builddir: Path = builddir
        self.cp: CP = cp.clone(self.builddir / cp.name)
        self.crs = Path(os.getenv("JAVA_CRS_SRC"))
        Config().set_num_test_harnesses(len(self.cp.get_harnesses()))

    def run_static_analysis_server(self):
        cmd = [ (self.workdir / "run_static_ana_server.sh").absolute().as_posix(), self.cp.base.absolute().as_posix() ]
        for harness_cls_dir in self.harness_cls_dirs:
            cmd.append(str(harness_cls_dir.absolute()))

        run_cmd(cmd, cwd=self.workdir)

    # I intentionally put every prepare step that should not be used during competition in a separate function
    def prepare(self):
        LOG.info(f"Prepare {self.cp.name}")

        if DEV:
            # Second, build the CP based on our jazzer image
            # self.project.git_restore()
            # The following will fail in the competition (The image will be
            # pre-built and the dockerfile is not guaranteed to work)
            self.cp.build_docker_images()
            self.cp.build(True)

    def build_cp(self):
        LOG.info(f"Building {self.cp.name}")
        self.cp.build(True)

    def preparing_harnesses(self) -> list[Path]:
        wrapper_harnesses: list[Harness] = []
        generated_harnesses: list[Harness] = []
        concolic_harnesses: list[Harness] = []
        generated_tasks: list[AsyncResult] = []
        concolic_tasks: list[AsyncResult] = []

        generator = HarnessGenerator(self.cp, self.crs, self.workdir)
        q_listener, queue = pool_logger_init()
        pool = ThreadPool(Config().thread_num, pool_init, [queue])

        len_test_hanresses = len(self.cp.get_harnesses())
        n_harness = (Config().thread_num - len_test_hanresses) // (1.3)
        n_gen_harness = 0

        for benchmark in self.cp.get_harnesses():
            if n_harness - n_gen_harness < 2:
                break
            wrapper_harness = generator.generate_harness_wrapper(
                benchmark.id, benchmark.source
            )
            wrapper_harnesses.append(wrapper_harness)
            n_gen_harness += 1

        self.wrapper_harnesses = wrapper_harnesses

        pool.map(
            partial(_compile_harness, workdir=self.workdir), self.wrapper_harnesses
        )

        for benchmark in self.cp.get_harnesses():
            if n_harness - n_gen_harness < 2:
                break
            generated_harness = pool.apply_async(generator.generate_and_compile, args=(benchmark, "jazzer"))
            generated_tasks.append(generated_harness)
            n_gen_harness += 1

        for benchmark in self.cp.get_harnesses():
            if n_harness - n_gen_harness < 2:
                break
            generated_harness = pool.apply_async(generator.generate_and_compile, args=(benchmark, "proto"))
            generated_tasks.append(generated_harness)
            n_gen_harness += 1
        

        left_core = int(n_harness - n_gen_harness)
        Config().set_left_core(left_core)


        generated_harnesses = [harness for task in generated_tasks if (harness := task.get()) is not None]

        self.generated_harnesses = generated_harnesses

        generator.copy_to(
            self.builddir / "harnesses/"
        )  # To see the generated harnesses

        pool.close()
        pool.join()
        q_listener.stop()

        fuzzing_manager = FuzzingManager(self.crs, self.builddir)
        # collect harness dirs
        self.harness_cls_dirs = []
        for harness in self.wrapper_harnesses:
            self.harness_cls_dirs.append(harness.harness_dir / harness.class_name)
            # Run the dictionary generator
            t = threading.Thread(target=harness.run_dict_gen, args=(self.workdir.absolute().as_posix(),))
            t.start()
        fuzzing_manager.register_harnesses(self.wrapper_harnesses)
        for harness in self.generated_harnesses:
            self.harness_cls_dirs.append(harness.harness_dir / harness.class_name)
        fuzzing_manager.register_harnesses(self.generated_harnesses)

    def preparing_concolic_harnesses(self) -> list[Path]:
        concolic_harnesses: list[Harness] = []
        concolic_tasks: list[AsyncResult] = []

        generator = HarnessGenerator(self.cp, self.crs, self.workdir)

        harnesses = self.cp.get_harnesses()
        pool = ThreadPool(len(harnesses))

        for benchmark in harnesses:
            generated_harness = pool.apply_async(generator.generate_and_compile, args=(benchmark, "concolic"))
            concolic_tasks.append(generated_harness)

        self.concolic_harnesses = [harness for task in concolic_tasks if (harness := task.get()) is not None]

        generator.copy_to(self.builddir / "harnesses/")

        pool.close()
        pool.join()

    def prepare_for_run(self):
        # Run joern HTTP server
        tasks = []

        LOG.info("Preparing harnesses")
        self.preparing_harnesses()
        self.preparing_concolic_harnesses()

        # to get full icfg info, static analysis server should be started after the harnesses are compiled
        LOG.info("Running static analysis server")
        proc2 = multiprocessing.Process(
            target=self.run_static_analysis_server,
        )
        proc2.start()
        tasks.append(proc2)

        return tasks
    
    def __phase_commit_analyzer(self, output_file: Path):
        verifier = self.crs / "verifier" / "verifier.py"

        cmd = ["python3", str(verifier), "--precompile"]
        run_cmd(cmd)

        LOG.info(f"Running commit analyzer on {self.cp.name}")

        cmd = f"python3 run.py -t {str(self.cp.base)} -w {str(self.workdir)} --output {str(output_file)} --max_worker 5 --print_cost --config commitmulticlassconfig"
        try:
            subprocess.run(cmd.split(" "), cwd=self.crs / "commit-analyzer", capture_output=True, timeout=Config().commit_analyzer_timeout)
        except subprocess.TimeoutExpired:
            LOG.error(f"Commit analyzer is timed out after {Config().commit_analyzer_timeout} seconds.")
            return

        if output_file.exists():
            # call verifier --precompile
            os.environ["BIC_HINTS"] = str(output_file)
            cmd = ["python3", str(verifier), "--precompile"]
            run_cmd(cmd)
            return output_file
        else:
            LOG.error(f"Failed to run commit analyzer on {self.cp.name}")
    
    def phase_commit_analyzer(self):
        output_file = self.workdir / "commit_analyzer_output.txt"
        if Config().is_main():
            self.__phase_commit_analyzer(output_file)
            self.to_shared_file(output_file)
        else:
            dst = self.from_shared_file(output_file)
            if dst:
                os.environ["BIC_HINTS"] = str(dst)

    def get_shared_path(self, path):
        shared_dir = self.builddir / "shared_output"
        os.makedirs(shared_dir, exist_ok = True)
        return shared_dir / path.name

    def to_shared_file(self, src):
        dst = self.get_shared_path(src)
        copy(src, dst)
        return SharedFile(dst).finalize()

    def from_shared_file(self, dst):
        src = self.get_shared_path(dst)
        shared_src = SharedFile(src)
        shared_src.wait()
        copy(src, dst)
        if dst.exists():
            logging.info(f"Successfully copy from shared file: {src} => {dst}")
            return dst
        else:
            logging.info(f"Fail to copy from shared file: {src} => {dst}")
            return None


    
    async def phase_llm_poc(self, n, temperature):
        llm_poc_runner = LLMPoCRunner(self.cp, self.crs, self.builddir)
        used_llm_cost = await llm_poc_runner.run(n,temperature)
        return used_llm_cost

    def phase_concolic(self, pool, fuzzing_manager:FuzzingManager):
        LOG.info(f"Running concolic on {self.cp.name} {self.builddir}/harnesses/")
        LOG.info(f"Concolic workdir {self.workdir}")

        for concolic_harness in self.concolic_harnesses:
            pool.apply(concolic_harness.run_concolic, args=(self.workdir,self.builddir,))

    def phase_fuzzing_one(self, pool, fuzzing_manager:FuzzingManager):
        LOG.info(f"Running fuzzing phase one on {self.cp.name}")

        for generated_harness in self.generated_harnesses:
            if not generated_harness.directed_fuzzing:
                pool.apply_async(generated_harness.run, args=(self.workdir,))

    def phase_fuzzing_two(self, pool, fuzzing_manager:FuzzingManager):
        LOG.info("Starting Joern server")
        proc = multiprocessing.Process(target=run_joern_server)
        proc.start()

        # LOG.info("Kill fuzzers ran on Phase 1")
        # for harness in self.generated_harnesses:
        #     if harness.fuzzer:
        #         kill_process_tree(harness.fuzzer.pid)
        #         harness.fuzzer = None

        LOG.info(f"Running fuzzing phase two on {self.cp.name}")

        for wrapper_harness in self.wrapper_harnesses:
            pool.apply(wrapper_harness.run, args=(self.workdir, True))
        
        # pool.map_async(partial(_run_fuzzer, workdir=self.workdir, crs=self.crs) , wrapper_harnesses)

        for generated_harness in self.generated_harnesses:
            if generated_harness.directed_fuzzing:
                pool.apply_async(generated_harness.run, args=(self.workdir,))



    def run_dev(self):
        # TODO: use asyncio instead of threading and multiprocessing

        start_time = time.time()
        # loop = asyncio.get_event_loop()

        # init_llm_poc_task = asyncio.wait([loop.create_task(self.phase_llm_poc(10, 1.0))], return_when=asyncio.FIRST_COMPLETED)



        # Will kill verifier thread after 4 hours
        povmanager = PoVManager(self.crs)
        verifier = threading.Thread(target=asyncio.run, args=(povmanager.check(),))
        verifier.start()

        fuzzing_manager = FuzzingManager(self.crs, self.builddir)
        fm_instance = threading.Thread(target=asyncio.run, args=(fuzzing_manager.check(),))
        fm_instance.start()

        prepare_tasks = self.prepare_for_run()

        q_listener, queue = pool_logger_init()
        pool = ThreadPool(Config().thread_num, pool_init, [queue])
        self.phase_fuzzing_two(pool, fuzzing_manager)

        # will change the 2nd arg to get the scheduling feedback
        concolic_runner_count = len(self.cp.get_harnesses())
        LOG.info(f'Concolic runner count: {concolic_runner_count}')
        concolic_pool = ThreadPool(concolic_runner_count)
        self.phase_concolic(concolic_pool, None)
        
        # done, _pending = loop.run_until_complete(init_llm_poc_task)
        # used_llm_cost = done.pop().result()

        # it = 1
        # while time.time() - start_time < Config().entire_running_time:
        #     if used_llm_cost > Config().llm_poc_budget or it > Config().llm_poc_max_iteration:
        #         break
        #     n = random.randrange(5, 12)
        #     temperature = random.uniform(0.0, 2.0)
        #     # if it == 1:
        #     #     n, temperature = 10, 1.0
        #     used_llm_cost += loop.run_until_complete(self.phase_llm_poc(n, temperature))
        #     it += 1
        #     # time.sleep(Config().llm_poc_interval + it * 10)

        # Wait for all tasks to finish

        pool.close()
        pool.join()

        # task_llm_poc.get(timeout=Config().entire_running_time)
        # verifier.get(timeout=Config().entire_running_time)
        verifier.join(timeout=Config().entire_running_time)

        for task in prepare_tasks:
            task.join()
            task.close()

        q_listener.stop()

    def run(self):
        # TODO: use asyncio instead of threading and multiprocessing

        os.environ["TARGET_CP"] = self.cp.name
        start_time = time.time()
        povmanager = PoVManager(self.crs)

        ### RUN checkers
        # Will kill verifier thread after 4 hours
        verifier = threading.Thread(target=asyncio.run, args=(povmanager.check(),))
        verifier.start()

        fuzzing_manager = FuzzingManager(self.crs, self.builddir)
        fm_instance = threading.Thread(target=asyncio.run, args=(fuzzing_manager.check(),))
        fm_instance.start()

        ### Preprocssing & run LLM_POC_GEN
        q_listener, queue = pool_logger_init()
        pool = ThreadPool(Config().thread_num, pool_init, [queue])

        commit_analyzer = pool.apply_async(self.phase_commit_analyzer, args=())

        llm_poc_runner = LLMPoCRunner(self.cp, self.crs, self.builddir)
        llm_poc_run = pool.apply_async(asyncio.run, args=(llm_poc_runner.run(10, 1.0),))

        prepare_tasks = self.prepare_for_run()

        self.phase_fuzzing_one(pool, fuzzing_manager)


        ### Fuzzing & Report LLM_POC_GEN result
        llm_poc_run.wait()
        llm_poc_end = pool.apply_async(asyncio.run, args=(llm_poc_runner.end_callback(),))
        llm_poc_end.wait()

        pool.apply_async(asyncio.run, args=(fuzzing_manager.add_corpus_from_llm(),))
        self.phase_fuzzing_two(pool, fuzzing_manager)
        llm_poc_result = pool.apply_async(asyncio.run, args=(llm_poc_runner.handle_result(),))

        # Wait for all tasks to finish

        # will change the 2nd arg to get the scheduling feedback
        concolic_runner_count = len(self.cp.get_harnesses())
        LOG.info(f'Concolic runner count: {concolic_runner_count}')
        # concolic_pool = ThreadPool(concolic_runner_count)
        self.phase_concolic(pool, None)

        used_llm_cost = llm_poc_result.get()


        
        # Wait for all tasks to finish
        pool.close()
        pool.join()

        # concolic_pool.close()
        # concolic_pool.join()

        # task_llm_poc.get(timeout=Config().entire_running_time)
        # verifier.get(timeout=Config().entire_running_time)
        verifier.join(timeout=Config().entire_running_time)
        fm_instance.join(timeout=Config().entire_running_time)

        # for task in prepare_tasks:
        #     task.join()
        #     task.close()

        q_listener.stop()



def _compile_harness(harness: Harness, workdir: Path):
    # stub for pool.map
    harness.compile(workdir)
