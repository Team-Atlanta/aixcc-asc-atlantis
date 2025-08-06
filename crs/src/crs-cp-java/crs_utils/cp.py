from pathlib import Path
import subprocess
import yaml

from .logfactory import LOG
from .settings import DEV
from .benchmark import Benchmark
from .utils import run_cmd
from .config import Config, distribute

def git_head(p):
    git_config_cmd = "git config --global --add safe.directory " + str(p)
    run_cmd(git_config_cmd.split(" "))
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd = p).strip()


class CP:
    def __init__ (self, base: Path):
        yaml_path = base / "project.yaml"
        with open(yaml_path, "r") as f:
            project_yaml = yaml.safe_load(f)
        self.base: Path = base
        self.name: str = project_yaml["cp_name"]
        self.lang: str = project_yaml["language"]
        self.sanitizers = {}
        for sanitizer_id, sanitizer_msg in project_yaml["sanitizers"].items():
            self.sanitizers[sanitizer_id] = sanitizer_msg
        self.harnesses: dict[str, Benchmark] = {}
        for harness_id, data in project_yaml["harnesses"].items():
            # if DEV:
            #     self.harnesses[harness_id] = Benchmark(self.base, harness_id, data["name"], Path(data["source"]), data["binary"], data["sanitizer"])
            # else:
            self.harnesses[harness_id] = Benchmark(self.base, harness_id, data["name"], Path(data["source"]), data["binary"])
        self.docker_image: str = project_yaml["docker_image"]
        self.sources: str = project_yaml["cp_sources"]
        self.harness_dirs: list[Path] = (base / "src").glob("*harness*")

    def clean(self):
        LOG.info(f"Clean {self.name} at {self.base}")
        run_cmd(["make", "clean"], cwd = self.base)

    def build(self, prebuild=False):
        # if prebuild:
        #     # FIXME: prebuild is not required for release
        #     LOG.info(f"Prebuild {self.name} at {self.base}")
        #     self.run_sh(cmd="prebuild")

        LOG.info(f"Build {self.name} at {self.base}")
        self.run_sh(cmd="build")
    
    def build_reset(self):
        LOG.info(f"Build reset {self.name} at {self.base}")
        for _harness_id, benchmark in self.harnesses.items():
            if benchmark.binary.exists():
                benchmark.binary.unlink()

    
    def is_built(self):
        for _harness_id, benchmark in self.harnesses.items():
            if benchmark.binary.exists() == False:
                return False
        return True

    def clone(self, dst: Path):
        if dst.exists():
            if git_head(dst) == git_head(self.base):
                return CP(dst)
        run_cmd(["rm", "-rf", dst.absolute().as_posix()])
        run_cmd(["cp", "-r", self.base.absolute().as_posix(), dst.absolute().as_posix()])
        return CP(dst)

    def git_restore(self):
        LOG.info(f"Git restore {self.name} at {self.base}")
        run_cmd(["git", "restore", "."], cwd = self.base)
    
    def build_docker_images(self):
        LOG.info(f"Build docker image for {self.name} at {self.base}")
        run_cmd(["make", "docker-build", "DOCKER_IMAGE_NAME=" + self.docker_image], cwd = self.base)

    def run_sh(self, cmd):
        LOG.debug(f"Run {cmd}")

        proc = None
        e_cmd = "./run.sh " + cmd
        if cmd == "build" or cmd == "prebuild":
            # Do not capture the output of build and prebuild to know progress
            subprocess.run(e_cmd.split(" "), cwd = self.base)
        else:
            proc = run_cmd(e_cmd.split(" "), cwd = self.base)
        return proc

    def get_harnesses(self) -> list[Benchmark]:
        benchmarks = self.harnesses.values() 

        jobs = Config().distribute_job(benchmarks)
        
        if Config().is_main():
            benchmarks = jobs[0]
        elif Config().is_worker():
            benchmarks = jobs[1]

        return benchmarks
    
    def get_harness(self, harness_id: str) -> Benchmark:
        return self.harnesses[harness_id]
    
    def get_sanitizer_msg(self, sanitizer_id: str) -> str:
        return self.sanitizers[sanitizer_id]
    
    def get_sanitizer_id(self, error_logs) -> str:
        for sanitizer_id, sanitizer_msg in self.sanitizers.items():
            if sanitizer_msg in error_logs:
                return sanitizer_id
        return None
