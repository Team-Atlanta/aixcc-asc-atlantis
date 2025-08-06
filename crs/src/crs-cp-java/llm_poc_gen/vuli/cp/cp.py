from vuli.common.decorators import consume_exc_method
from vuli.common.singleton import Singleton
from vuli.common.util import path_validation
from vuli.vuln import Vuln
import glob
import os
import subprocess
import tempfile
import yaml


class CP(metaclass=Singleton):
    cp_dir = ""
    dependency_dir = ""
    project_yaml = ""
    run_script = ""
    __blob_path = ""
    source_dirs = []
    sanitizers = {}

    def __init__(self):
        pass

    def load(self, cp_dir: str):
        self.cp_dir = os.path.realpath(cp_dir)
        self.run_script = os.path.join(self.cp_dir, "run.sh")
        self.project_yaml = os.path.join(self.cp_dir, "project.yaml")
        self.source_dirs = list(
            map(lambda x: os.path.join(self.cp_dir, x), ["src", "container_scripts"])
        )
        self.dependency_dir = os.path.join(self.cp_dir, "out", "harnesses")
        self.__blob_path = os.path.join(self.cp_dir, "work", "tmp_blob")
        path_validation(
            [self.cp_dir, self.dependency_dir, self.project_yaml, self.run_script]
            + self.source_dirs
        )

        with open(self.project_yaml, "r") as f:
            root = yaml.safe_load(f)
            self.harnesses = root["harnesses"]
            self.sanitizers = root["sanitizers"]

        # Register sentinels
        Vuln().clean_sentinels()
        Vuln().add_sentinel(
            "OSCommandInjection", os.getenv("JAZZER_COMMAND_INJECTION", "jazze")
        )
        Vuln().add_sentinel(
            "ServerSideRequestForgery", os.getenv("JAZZER_SSRF", "jazzer.example.com")
        )
        Vuln().add_sentinel(
            "Deserialization",
            b"\xac\xed\x00\x05sr\x00\x07jaz.Zer\x00\x00\x00\x00\x00\x00\x00*\x02\x00\x01B\x00\tsanitizerxp\x02\n",
        )
        Vuln().add_sentinel("SqlInjection", "'")
        Vuln().add_sentinel("NamingContextLookup", "${jndi:ldap://g.co/}")
        Vuln().add_sentinel("NamingContextLookup", "${ldap://g.co/}")
        Vuln().add_sentinel("LdapInjection", "(")
        Vuln().add_sentinel("XPathInjection", "document(2)")
        Vuln().add_sentinel("ReflectiveCall", "jazzer_honeypot")
        Vuln().add_sentinel("RegexInjection", "*")
        Vuln().add_sentinel("ScriptEngineInjection", '"jaz"+"zer"')
        Vuln().add_sentinel(
            "ArbitraryFileReadWrite", os.getenv("JAZZER_FILE_READ_WRITE", "jazzer")
        )
        Vuln().add_sentinel(
            "ArbitraryFileReadWrite",
            os.getenv("JAZZER_FILE_SYSTEM_TRAVERSAL_FILE_NAME", "jazzer-traversal"),
        )

    def get_dependent_jars(self):
        jars = {}
        for jar in glob.glob(
            os.path.join(self.dependency_dir, "**", "*.jar"), recursive=True
        ):
            name = os.path.basename(jar)
            if name in jars:
                continue
            jars[name] = os.path.abspath(jar)
        return list(jars.values())

    @consume_exc_method(default="")
    def get_test_harness_path(self, harness_id: str) -> str:
        return self.harnesses[harness_id]["source"]

    # TODO : Should be interface method
    @consume_exc_method("")
    def get_harness_path(self, id: str) -> str:
        return self.harnesses[id]["source"]

    def get_test_harness_as_path_to_id(self):
        table = {}
        try:
            with open(self.project_yaml, "r") as f:
                harnesses = yaml.safe_load(f.read()).get("harnesses", {})
                for key, value in harnesses.items():
                    table[value["source"]] = key
        finally:
            return table

    def get_sanitizers_as_name_to_id(self):
        try:
            with open(self.project_yaml, "r") as f:
                data = yaml.safe_load(f)
            sanitizers = data["sanitizers"]
            return {v: k for k, v in sanitizers.items()}
        except:
            return {}

    def run_pov(self, test_harness_id: str, blob: bytes) -> set[str]:
        blob_file = tempfile.NamedTemporaryFile(delete=False)
        blob_file.write(blob)
        blob_file.flush()

        if os.path.exists(self.__blob_path):
            os.remove(self.__blob_path)

        test_harness_name = self.harnesses[test_harness_id]["name"]

        cmd = [self.run_script, "run_pov", blob_file.name, test_harness_name]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired as e:
            print("[W] Timeout")
            return False

        result: set[str] = set()
        msg = f"{res.stdout}\n{res.stderr}"
        for key, value in self.sanitizers.items():
            if not value in msg:
                continue

            result.add(key)

        return result
