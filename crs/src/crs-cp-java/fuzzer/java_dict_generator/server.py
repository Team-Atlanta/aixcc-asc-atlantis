import os
import glob
import time
import socket
import atexit
import subprocess

import argparse

from multiprocessing import Lock
from contextlib import contextmanager

from py4j.java_gateway import JavaGateway

import flask
from flask import Flask, request
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# add logging to file for flask service
#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
# handler = logging.StreamHandler(sys.stdout)
handler = logging.FileHandler("/tmp/static-ana-pyserver.log")
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# global variable
JAVA_PORT = 25333
WEB_URL = "0.0.0.0"
WEB_PORT = 9505

gateway = None
gatelock = Lock()
LOCKTIMEOUT = 5
java_log = "/tmp/java-dict-gen-server.log"
java_process = None


@contextmanager
def get_lock(lock, block=True, timeout=None):
    held = lock.acquire(block=block, timeout=timeout)
    try:
        yield held
    finally:
        if held:
            lock.release()


@app.route("/rankbranch", methods=["POST"])
def rankbranch():
    global gateway, gatelock, LOCKTIMEOUT

    if request.method == "POST":
        with get_lock(gatelock, True, LOCKTIMEOUT) as success:
            if not success:
                app.logger.error("rankBranch get_lock failed")
                return flask.jsonify({"getLock": False})

            try:
                data = request.get_json()

                stuck_branch_file = data["stuckBranchFile"]
                ranked_branch_file = data["rankedBranchFile"]

                success = gateway.entry_point.rankBranch(
                    stuck_branch_file, ranked_branch_file
                )
                app.logger.info(f"rankBranch success: {success}")
                return flask.jsonify({"getLock": True, "success": success})

            except Exception as e:
                app.logger.error(f"rankBranch error: {e}")
                return flask.jsonify({"getLock": True, "success": False})


@app.route("/gendict", methods=["POST"])
def gendict():
    global gateway, gatelock, LOCKTIMEOUT

    if request.method == "POST":
        with get_lock(gatelock, True, LOCKTIMEOUT) as success:
            if not success:
                app.logger.error("genDict get_lock failed")
                return flask.jsonify({"getLock": False})

            try:
                data = request.get_json()

                target_class = data["targetClass"]
                target_method = data["targetMethod"]
                output_dict = data["outputDict"]
                print("data:", data)
                if "focused" in data and data["focused"] == "true":
                    success = gateway.entry_point.genDictFocused(
                        target_class, target_method, output_dict
                    )
                else:
                    success = gateway.entry_point.genDict(
                        target_class, target_method, output_dict
                    )
                app.logger.info(f"genDict success: {success}")
                return flask.jsonify({"getLock": True, "success": success})

            except Exception as e:
                app.logger.error(f"genDict error: {e}")
                return flask.jsonify({"getLock": True, "success": False})


@app.route("/issootinited", methods=["GET"])
def issootinited():
    global gateway, gatelock, LOCKTIMEOUT

    with get_lock(gatelock, True, LOCKTIMEOUT) as success:
        if not success:
            app.logger.error("isSootInited get_lock failed")
            return flask.jsonify({"getLock": False})

        app.logger.info(f"isSootInited: {gateway.entry_point.isSootInited()}")
        return flask.jsonify(
            {
                "getLock": True,
                "isSootInited": gateway.entry_point.isSootInited(),
            }
        )


# old approach, deprecated
def deprecated_find_classpath(proj_src, harness_dirs):
    """
    $(find "${SRC}" -name "classpath" -type d -exec find {} -type f -name "*.jar" -printf "%p:" \;)
    $(find "${SRC}" -name "build" -type d -printf "%p:")
    """
    app.logger.info(f"proj_src: {proj_src} harness_dirs: {harness_dirs}")

    # Initialize classpath
    classpath = [d for d in harness_dirs]

    # Find .jar files in 'classpath' directories
    for dirpath, _, _ in os.walk(proj_src):
        if os.path.basename(dirpath) == "classpath":
            jar_files = glob.glob(os.path.join(dirpath, "**", "*.jar"), recursive=True)
            classpath.extend(jar_files)

    # Find 'build' directories
    for dirpath, dirnames, filenames in os.walk(proj_src):
        if os.path.basename(dirpath) == "build":
            classpath.append(dirpath)

    # Print the paths
    app.logger.info(f"classpath: {':'.join(classpath)}")

    return ":".join(classpath)


def find_classpath(proj_src, harness_dirs):
    """
    find all nested .jar files in proj_src, and append harness_dirs
    """
    app.logger.info(f"proj_src: {proj_src} harness_dirs: {harness_dirs}")

    # Initialize classpath
    classpath = [d for d in harness_dirs]

    # Find all .jar files in this directories
    jar_files = glob.glob(os.path.join(proj_src, "**", "*.jar"), recursive=True)
    classpath.extend(jar_files)

    # Print the paths
    app.logger.info(f"classpath: {':'.join(classpath)}")

    return ":".join(classpath)


# python server gracefully shutdown
@atexit.register
def shutdown_server():
    global java_process
    if java_process:
        java_process.kill()
        java_process.wait()
        app.logger.info("Shutting down Java side!")


def check_port_is_listen(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def check_java_side_is_up(java_proc):
    while True:
        if java_proc.poll() is not None:
            app.logger.info("Java process has been terminated!")
            return False

        if check_port_is_listen(JAVA_PORT):
            app.logger.info("Java process is up!")
            return True

        time.sleep(1)


def py4j_init(javajarpath, cplocation, harnessdirs):
    global gateway, java_log, java_process

    classpath = find_classpath(cplocation, harnessdirs)

    try:
        # run java side as background process
        app.logger.info("Starting java process...")
        with open(java_log, "w") as f:
            # store stdout/stderr output
            java_process = subprocess.Popen(
                f"java -jar {javajarpath} server",
                shell=True,
                stdout=f,
                stderr=subprocess.STDOUT,
            )

        check_java_side_is_up(java_process)

        app.logger.info("Starting py4j gateway...")
        # run python side
        gateway = JavaGateway()

        app.logger.info("Setting up Soot...")
        java_list = gateway.jvm.java.util.ArrayList()
        for harnessdir in harnessdirs:
            java_list.append(harnessdir)
        gateway.entry_point.setupSoot(classpath, java_list)
        while not gateway.entry_point.isSootInited():
            time.sleep(5)

        app.logger.info("Soot is inited, start serving!")

    except Exception as e:
        app.logger.error(f"Error: {e}")
        exit(1)


def main():
    global WEB_URL, WEB_PORT

    parser = argparse.ArgumentParser(
        description="Run the API server for java static analyzer"
    )
    parser.add_argument(
        "-j",
        "--javajarpath",
        required=True,
        type=str,
        help="Java jar path, for running java code",
    )
    parser.add_argument(
        "-cp",
        "--cplocation",
        required=True,
        type=str,
        help="Cp jenkins location, for searching classes & jars",
    )
    parser.add_argument(
        "-d",
        "--harnessdirs",
        required=True,
        nargs="+",
        default=[],
        help="Harness directory, containing classes, dict, etc",
    )
    args = parser.parse_args()

    app.logger.info("args.javajarpath:" + str(args.javajarpath))
    app.logger.info("args.cplocation:" + str(args.cplocation))
    app.logger.info("args.harnessdirs:" + str(args.harnessdirs))

    app.logger.info("=== start running java code using py4j ===")
    py4j_init(args.javajarpath, args.cplocation, args.harnessdirs)

    app.logger.info("=== start running HTTP server ===")
    # TODO: should we consider the case that the port is already in use?
    app.run(WEB_URL, WEB_PORT)


if __name__ == "__main__":
    main()
