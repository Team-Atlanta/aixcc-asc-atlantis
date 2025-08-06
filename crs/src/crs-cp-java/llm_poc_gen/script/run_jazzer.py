import argparse
import glob
import os
import shutil
import subprocess
import tempfile

root_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def handle_commandline() -> tuple[str, str, str, str]:
    parser = argparse.ArgumentParser(description="Jazzer Helper Script")
    parser.add_argument("--cp_dir", type=str, required=True, help="CP Directory")
    parser.add_argument(
        "--jazzer_dir", type=str, required=True, help="Jazzer Directory"
    )
    parser.add_argument(
        "--fuzzer_driver", type=str, required=True, help="Fuzzer Driver Source Code"
    )
    parser.add_argument("--custom_mutator", type=str, help="Custom Mutator Path")

    args = parser.parse_args()
    return (os.path.realpath(args.cp_dir), os.path.realpath(args.jazzer_dir), args.fuzzer_driver, args.custom_mutator)


def get_class_path(cp_dir: str, jazzer_dir: str) -> str:
    cp_src_dir = os.path.join(cp_dir, "src")
    cp_easy_test_dir = os.path.join(cp_src_dir, "easy-test")
    cp_class_path_dir = os.path.join(cp_easy_test_dir, "classpath")
    cp_work_dir = os.path.join(cp_dir, "work")

    class_path = ":".join(glob.glob(os.path.join(jazzer_dir, "*.jar")))
    class_path += f":{":".join(glob.glob(os.path.join(cp_class_path_dir, "jenkins-war", "**", "*.jar"), recursive=True))}"
    class_path += f":{":".join(glob.glob(os.path.join(cp_class_path_dir, "other", "**", "*.jar"), recursive=True))}"
    class_path += f":{":".join(glob.glob(os.path.join(cp_class_path_dir, "plugins", "**", "*.jar"), recursive=True))}"
    class_path += f":{os.path.join(cp_easy_test_dir, "build")}"
    class_path += f":{os.path.join(cp_work_dir, "maven_repo", "org", "kohsuke", "stapler", "stapler", "1822.v120278426e1c", "stapler-1822.v120278426e1c.jar")}"
    class_path += f":{os.path.join(cp_src_dir, "javax-servlet-api-4.0.1.jar")}"
    return class_path


def prepare_workspace(fuzzer_driver: str) -> str:
    workspace = os.path.join(root_dir, "workspace")
    os.makedirs(workspace, exist_ok=True)

    workspace = tempfile.TemporaryDirectory(dir=workspace, delete=False)
    shutil.copy(fuzzer_driver, os.path.join(workspace.name, os.path.basename(fuzzer_driver)))
    return workspace.name


def compile_fuzzer_driver(workspace: str, fuzzer_driver: str, cp_dir: str, jazzer_dir: str) -> bool:
    fuzzer_driver_in_workspace = os.path.join(workspace, os.path.basename(fuzzer_driver))
    print(get_class_path(cp_dir, jazzer_dir))
    cmd = [
        "javac",
        "-cp",
        get_class_path(cp_dir, jazzer_dir),
        fuzzer_driver_in_workspace
    ]
    return subprocess.run(cmd).returncode == 0

def run_jazzer(workspace: str, fuzzer_driver: str, custom_mutator: str, cp_dir: str, jazzer_dir: str):
    os.makedirs(os.path.join(workspace, "queue"), exist_ok=True)
    cmd = [
        os.path.join(jazzer_dir, "jazzer"),
        f"--agent_path={os.path.join(jazzer_dir, "jazzer_standalone_deploy.jar")}",
        f"--cp={get_class_path(cp_dir, jazzer_dir)}",
        f"--disabled_hooks=com.code_intelligence.jazzer.sanitizers.IntegerOverflow",
        f"--jvm_args=-Djdk.attach.allowAttachSelf=true:-Djenkins.security.ClassFilterImpl.SUPPRESS_ALL=true:-XX\:+StartAttachListener",
        f"--target_class={os.path.basename(fuzzer_driver)[:-5]}",
        f"-runs=1000",
        "queue"
    ]
    print(cmd)
    env = os.environ.copy()
    if custom_mutator:
        env["LD_PRELOAD"] = custom_mutator
    
    subprocess.run(cmd, cwd=workspace)


def create_jazzer_command_line(cp_dir: str, jazzer_dir: str) -> list[str]:
    jazzer = os.path.join(jazzer_dir, "jazzer")
    jazzer_agent = os.path.join[jazzer_dir, "jazzer_standalone_deploy.jar"]

    cp_src_dir = os.path.join(cp_dir, "src")
    cp_easy_test_dir = os.path.join(cp_src_dir, "easy-test")
    cp_class_path_dir = os.path.join(cp_src_dir, "classpath")
    cp_work_dir = os.path.join(cp_dir, "work")

    class_path = ":".join(
        glob.glob(
            os.path.join(cp_easy_test_dir, "classpath", "**", "*.jar", recursive=True)
        )
    )
    class_path += f":{os.path.join(cp_easy_test_dir, "build")}"
    class_path += f":{jazzer_dir}"
    class_path += f":{os.path.join(cp_class_path_dir, "jenkins-war")}"
    class_path += f":{os.path.join(cp_class_path_dir, "other")}"
    class_path += f":{os.path.join(cp_class_path_dir, "plugins")}"
    # TODO: Add directoty that fuzzer class file exist
    class_path += f":{os.path.join(cp_work_dir, "maven_repo", "org", "kohsuke", "stapler", "stapler", "1822.v120278426e1c", "stapler-1822.v120278426e1c.jar")}"
    class_path += f":{os.path.join(cp_src_dir, "javax-servlet-api-4.0.1.jar")}"
    return [jazzer, f"--agent_path={jazzer_agent}" f"--cp={class_path}"]


def main():
    cp_dir, jazzer_dir, fuzzer_driver, custom_mutator = handle_commandline()
    workspace = prepare_workspace(fuzzer_driver)
    print (f"[I] workspace is prepared at {workspace}")

    res = compile_fuzzer_driver(workspace, fuzzer_driver, cp_dir, jazzer_dir)
    if res == False:
        print (f"[E] Failed to build fuzzer driver")
        return
    print (f"[I] fuzzer driver is prepared")

    run_jazzer(workspace, fuzzer_driver, custom_mutator, cp_dir, jazzer_dir)
    print (f"[I] Finished")


if __name__ == "__main__":
    main()
