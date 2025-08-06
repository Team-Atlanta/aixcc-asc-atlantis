import os
from pathlib import Path

from .harness import Harness
from .cp import CP
from .utils import run_cmd
from .logfactory import LOG
from .benchmark import Benchmark
from .config import Config


class HarnessGenerator:
    def __init__ (self, cp, crs, workdir):
        self.cp: CP = cp
        self.crs: Path = crs
        self.workdir:Path = workdir
        self.fuzzer = crs / "fuzzer"
        self.harness_dir: Path = self.workdir / "harnesses" / self.cp.name
        self.harness_dir.mkdir(parents = True, exist_ok = True)

    def copy_to(self, dst: Path):
        os.system("rm -rf " + dst.absolute().as_posix())
        dst.mkdir(parents = True, exist_ok = True)
        run_cmd(["cp", "-r", self.harness_dir, dst])

    def generate_and_compile(self, benchmark: Benchmark, mode):
        is_compiled = False

        it = 0
        threshold = Config().retry_harness_gen

        while not is_compiled and it < threshold:
            if mode == 'concolic':
                harness = self.generate_harness_concolic(benchmark, mode)
            else:
                harness = self.generate(benchmark, mode)
            is_compiled = harness.compile(self.workdir)
            if not is_compiled:
                harness.remove()
            it += 1

        if not is_compiled:
            return None

        return harness

    def generate(self, benchmark: Benchmark, mode):
        harness_id = benchmark.id
        harness_source = benchmark.source
        out_dir = self.harness_dir

        if mode != "proto" and mode != "jazzer":
            raise ValueError(f"Unknown harness mode: {mode}")

        orig_class_name = harness_source.with_suffix("").name

        cmd = ["python3", self.fuzzer / "java_harness_processor" / "main.py",
               "-o", out_dir, self.cp.base, harness_id]
        
        # if not DEV:
        cmd.extend(["-p", "llm"])

        if mode == "proto":
            # this generates both harnesses & .proto files
            cmd.append("--include-origin")
            harness_generated = out_dir / (orig_class_name + "_Fuzz.java")
            directed_fuzzing = True

        else:
            cmd.extend(["-f", mode])
            harness_generated = out_dir / (orig_class_name + "_JazzerFuzz.java")
            directed_fuzzing = False
        
        run_cmd(cmd)


        if mode == "proto":
            proto_file = harness_generated.with_suffix(".proto")
            if proto_file.exists():
                mode = "proto"
            else:
                # If the proto file does not exist, it means that the harness is generated for jazzer
                # due to composite mode
                mode = "jazzer"
                harness_generated = out_dir / (orig_class_name + "_CJazzerFuzz.java")

        class_name = harness_generated.with_suffix("").name

        LOG.info(f"Generated {mode} harness: {harness_generated}")

        return Harness(class_name, mode, self.cp, self.harness_dir, harness_id, harness_generated, orig_class_name, directed_fuzzing)

    def generate_harness_concolic(self, benchmark: Benchmark, mode) -> Harness:
        harness_id = benchmark.id
        harness_source = benchmark.source
        out_dir = self.harness_dir

        if mode != "concolic":
            raise ValueError(f"Unknown harness mode: {mode}")

        orig_class_name = harness_source.with_suffix("").name

        LOG.info(f"Generating concolic harness for {harness_id}")
        run_cmd(["python3", self.fuzzer / "java_harness_processor" / "main.py",
                 "-o", out_dir, "-f", "concolic", "-p", "llm",
                 self.cp.base, harness_id])
            
        harness_generated = out_dir / (orig_class_name + "_Concolic.java")
        directed_fuzzing = False
        class_name = harness_generated.with_suffix("").name

        LOG.info(f"Generated {mode} harness: {harness_generated}")

        return Harness(class_name, mode, self.cp, self.harness_dir, harness_id, harness_generated, orig_class_name, directed_fuzzing)


    def generate_harness_wrapper(self, harness_id: str, harness_source: Path) -> Harness:
        # Create a wrapper for the harness
        orig_class_name = harness_source.with_suffix("").name
        harness_wrapper = self.harness_dir / (orig_class_name + "_NaiveWrapper.java")
        run_cmd(["cp", harness_source, harness_wrapper], cwd = self.cp.base)
        class_name = harness_wrapper.with_suffix("").name
        need_init = False

        with open(harness_wrapper, "r") as f:
            content = f.read().replace("public class", "class")
            content_lines = content.split("\n")
            for i, line in enumerate(content_lines):
                if "package" in line:
                    content_lines[i] = ""
                if "fuzzerInitialize()" in line and "public static void" in line:
                    need_init = True

            content = "\n".join(content_lines)

        wrapper = f"public class {class_name} {{"

        if need_init:
            wrapper += """
            public static void fuzzerInitialize() throws Throwable {
                """
            wrapper += f"{orig_class_name}.fuzzerInitialize();"
            wrapper += """
            }
            """

        wrapper += """
        public static void fuzzerTestOneInput(byte[] data) throws Throwable {
            if (data == null) return;
            if (data.length == 0) return;
        """

        wrapper += f"{orig_class_name}.fuzzerTestOneInput(data);"
        wrapper += """

        }
    }
    """

        with open(harness_wrapper, "w") as f:
            prefix = "import java.io.FileNotFoundException;\n"
            content = prefix + "\n" + content + "\n" + wrapper
            f.write(content)

        LOG.info(f"Generated harness wrapper: {harness_wrapper}")

        return Harness(class_name, "naive", self.cp, self.harness_dir, harness_id, harness_wrapper, orig_class_name, False)
