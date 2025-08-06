import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .asynctask import AsyncTask
from .settings import DEV
from .cp import CP
from .povmanager import PoVManager, ReportStatus
from .utils import empty_function, run_sh_lock
from .config import Config
from .fuzzingmanager import FuzzingManager
import time
import psutil

class LLMPoCRunner(AsyncTask):
    def __init__(self, cp: CP, crs: Path, builddir: Path):
        self.cp = cp
        self.crs = crs
        self.llm_poc_gen_dir = self.crs / "llm_poc_gen"
        self.crs_joern_dir = self.crs / "joern" / "Joern"
        self.llm_poc_gen_output_dir = builddir / "llm_poc_gen_output"
        self.joern_dir = builddir / "joern"
        self.joern_port = 9000
        self.builddir = builddir
        super().__init__()
        self.LOG = self.logging_init("llm_poc_gen")

    def __install_joern_for_llm_poc_gen(self, joern_dir):
        self.LOG.info("Installing Joern for llm_poc_gen")
        subprocess.run(["./install_joern.sh", self.crs_joern_dir, joern_dir], cwd=self.llm_poc_gen_dir / "script")
    
    def kill_joern_process(self, start_time):
        for proc in psutil.process_iter():
            if "java" in proc.name() and "io.joern.joerncli.console.ReplBridge" in " ".join(proc.cmdline()):
                proc_start_time = proc.create_time()
                if proc_start_time >= start_time:
                    self.LOG.info(f"Killing Joern process: {proc.info['pid']}") 
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.TimeoutExpired:
                        self.LOG.info(f"Force killed Joern process with PID {proc.info['pid']}")
                        proc.kill()

    async def run(self, n, temperature):
        joern_build_dir = self.joern_dir / "joern-cli/target/universal/stage"

        if DEV and not joern_build_dir.exists():
            if joern_build_dir.exists():
                self.LOG.info(f"Joern is already installed in {self.joern_dir}")
            else:
                # Remove it after Saumya's joern is completed.
                # self.__install_joern_for_llm_poc_gen(self.joern_dir)
                pass

        if os.getenv("LITELLM_KEY") is None:
            self.LOG.error("LITELLM_KEY is not set; llm_poc_gen will not run.")
            return

        cmd = f"python3 -u -m vuli.main --cp_dir={self.cp.base} --output_dir={self.llm_poc_gen_output_dir} --n_response={n} --temperature={temperature}"
        # TODO: after porting to joern server
        # if not is_port_listening(self.joern_port):
        #     LOG.error(f"Port {self.joern_port} is not listening; check joern is installed")
        if not shutil.which("joern"):
            self.LOG.error("Joern is not installed; check local installation")
            if not self.joern_dir.exists():
                self.LOG.error(f"Joern is not installed in {self.joern_dir}; llm_poc_gen will not run.")
            else:
                cmd += f" --joern_dir={self.joern_dir}"

        self.LOG.info("Running llm_poc_gen")

        start_time = time.time()

        try:
            proc = subprocess.run(cmd.split(" "), cwd=self.llm_poc_gen_dir, timeout=Config().llm_poc_timeout)
        except subprocess.TimeoutExpired:
            self.LOG.error(f"llm_poc_gen is timed out after {Config().llm_poc_timeout} seconds.")
        
        try:
            self.kill_joern_process(start_time)
        except:
            pass
        
        # return await self.end_callback()

        # out = proc.stdout.decode("utf-8") + proc.stderr.decode("utf-8")

        # self.LOG.debug(out)

        # return await self.end_callback()


    async def end_callback(self):
        blackboard_path = self.llm_poc_gen_output_dir / "blackboard"
        llm_cost = 0

        self.LOG.info(f"llm_poc_gen end_callback: {blackboard_path}")
        fuzzing_manager = FuzzingManager(self.crs, self.builddir)

        if not blackboard_path.exists():
            self.LOG.error(f"llm_poc_gen failed. blackboard not found: {blackboard_path}")
            return

        with open(blackboard_path, "r") as f:
            blackboard = json.loads(f.read())

        # os.remove(blackboard_path)
        try:  
            if "tasks" in blackboard:
                tasks:list[dict] = blackboard["tasks"]

                for task in tasks:
                    if "cost" not in task:
                        continue
                    llm_cost += float(task["cost"])
                    if "blob" not in task:
                        continue
                    blobs: list[str] = task["blob"]
                    if "test_harness_id" not in task:
                        continue
                    harness_id = task["test_harness_id"]

                    for blob_content in blobs:
                        blob_content = base64.b64decode(blob_content)
                        with tempfile.NamedTemporaryFile(delete=False) as f:
                            f.write(blob_content)
                            blob_filename = f.name
                        
                        fuzzing_manager.add_corpus(harness_id, blob_filename)
        except Exception as e:
            self.LOG.error(f"Error in processing tasks: {str(e)}")

    async def handle_result(self):
        blackboard_path = self.llm_poc_gen_output_dir / "blackboard"
        llm_cost = 0

        self.LOG.info(f"llm_poc_gen handle_result: {blackboard_path}")

        pov_manager = PoVManager(self.crs)

        if not blackboard_path.exists():
            self.LOG.error(f"llm_poc_gen failed. blackboard not found: {blackboard_path}")
            return llm_cost

        with open(blackboard_path, "r") as f:
            blackboard = json.loads(f.read())

        if "result" not in blackboard:
            self.LOG.error(f"llm_poc_gen failed. result not found: {blackboard_path}")
            return llm_cost

        self.LOG.info(f"llm_poc_gen completed. {len(blackboard['result'])} PoV candidates are generated. llm_cost: {llm_cost}")

        for result in blackboard["result"]:
            if "harness_id" not in result or "blob" not in result:
                continue
            harness_id = result["harness_id"]
            blobs: list[str] = result["blob"]

            for blob_content in blobs:

                blob_content = base64.b64decode(blob_content)
                with tempfile.NamedTemporaryFile(delete=False) as f:
                    f.write(blob_content)
                    blob_filename = f.name


                res = await pov_manager.report(harness_id, blob_filename, self.cp, empty_function)

        # if not DEV:
        #     os.remove(blackboard_path)

        return llm_cost
