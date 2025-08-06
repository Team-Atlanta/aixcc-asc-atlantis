from vuli.common.decorators import consume_exc_method
from vuli.common.singleton import Singleton
from vuli.cp.cp import CP
from vuli.joern.joern_server import JoernServer
from vuli.joern.resource import Resource
import json
import os
import shutil
import subprocess
import tempfile


class Joern(metaclass=Singleton):
    joern_dir = ""
    joern_server: JoernServer = None

    def load(self, joern_dir):
        if joern_dir == None:
            self.joern = "joern"
            self.javasrc2cpg = "javasrc2cpg"
        else:
            self.joern = os.path.join(joern_dir, "joern")
            self.javasrc2cpg = os.path.join(
                joern_dir, "joern-cli", "frontends", "javasrc2cpg", "javasrc2cpg"
            )
        not_found_tools = list(
            filter(lambda x: shutil.which(x) is None, [self.joern, self.javasrc2cpg])
        )
        if len(not_found_tools) > 0:
            msg = ", ".join(not_found_tools)
            raise RuntimeError(f"Not Found Tool: {msg}")

    def build(self, output: str) -> None:
        exclude_dirs = os.listdir(CP().cp_dir)
        exclude_dirs = list(map(lambda x: os.path.join(CP().cp_dir, x), exclude_dirs))
        exclude_dirs = list(filter(lambda x: os.path.isdir(x), exclude_dirs))
        exclude_dirs = list(filter(lambda x: not x in CP().source_dirs, exclude_dirs))
        exclude_dirs = ",".join(exclude_dirs)

        dependent_jars = ",".join(CP().get_dependent_jars())

        env = os.environ.copy()
        env["JAVA_OPTS"] = "-Xmx12G"
        cmd = [
            self.javasrc2cpg,
            "--exclude",
            exclude_dirs,
            "--inference-jar-paths",
            dependent_jars,
            "-o",
            output,
            CP().cp_dir,
        ]
        subprocess.run(cmd, capture_output=True, env=env)

    def close_server(self):
        if self.joern_server == None:
            return

        self.joern_server.stop()
        self.joern_server = None

    def run_server(
        self, cpg_path: str, script_path: str, semantic: str, resource: Resource
    ) -> None:
        self.joern_output = tempfile.NamedTemporaryFile(delete=True)

        env = os.environ.copy()
        env["BASE_DIR"] = CP().cp_dir
        env["CPG_PATH"] = cpg_path
        env["OUT_PATH"] = self.joern_output.name
        env["SEMANTIC_DIR"] = semantic

        scripts = []
        with open(script_path, "r") as f:
            scripts.append(f.read())
            scripts.append("update_semantics")
            scripts.append("import_cpg")
        self.joern_server = JoernServer(
            self.joern,
            env,
            scripts,
            resource.get_timeout(),
            resource.get_memory(),
            resource.get_calldepth(),
        )

    @consume_exc_method(default=({}, True))
    def execute_query(self, query: str, timeout) -> tuple[dict, bool]:
        if self.joern_server.query(query, timeout=timeout)[1] == False:
            return ({}, False)
        with open(self.joern_output.name, "r") as f:
            return (json.load(f), True)

    def get_server(self) -> JoernServer:
        return self.joern_server
