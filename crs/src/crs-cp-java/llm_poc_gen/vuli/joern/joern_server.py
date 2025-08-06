from vuli.common.decorators import consume_exc_method
import psutil
import requests
import socket
import subprocess
import random
import time


class JoernServer:
    __memory: int = 12

    def __init__(self, joern, env, init_scripts=None, timeout=30, memory=12, init_timeout=600):
        self.joern = joern
        self.env = env
        self.__init_scripts = init_scripts if init_scripts else []
        self.__timeout = timeout
        self.__init_timeout = init_timeout
        self.__port = None
        self.__url = None
        self.__server = None
        self.__memory = memory
        self.start()

    @consume_exc_method(default=({}, False))
    def query(self, script, timeout=-1, restart_on_failure=True) -> tuple[dict, bool]:
        if not self.is_running():
            print(" - [W] Failed to query to stopped joern server", flush=True)
            return ({}, True)
        data = {"query": script}
        timeout = timeout if timeout > 0 else self.__timeout if timeout < 0 else None
        try:
            res = requests.post(self.__url, json=data, timeout=timeout)
            if res.status_code == 200:
                return (res.json(), True)
        except requests.Timeout:
            if restart_on_failure:
                print(f" - [W] Joern server query timeout({timeout})", flush=True)
                self.restart()
                return ({}, False)
        except requests.exceptions.RequestException:
            if restart_on_failure:
                print(f" - [W] Joern server query RequestException", flush=True)
                self.restart()
                return ({}, True)
        return ({}, True)

    def is_running(self) -> bool:
        return self.__server != None

    def stop(self):
        if not self.is_running():
            print(" - [W] Joern server is already stopped", flush=True)
            return
        try:
            print(" - [I] Joern server stop...", flush=True)
            parent = psutil.Process(self.__server.pid)
            children = parent.children(recursive=True)
            for child in children:
                child.terminate()
            _, still_alive = psutil.wait_procs(children, timeout=3)
            for p in still_alive:
                p.kill()
            self.__server.terminate()
            self.__server.wait(3)
        except Exception:
            print(" - [W] Joern server kill...", flush=True)
            self.__server.kill()
        self.__server = None

    def restart(self):
        self.stop()
        self.start()

    def start(self):
        def __assign_port():
            while True:
                port = random.randint(10000, 65535)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    if sock.connect_ex(("localhost", port)) != 0:
                        return port

        def __run() -> None:
            print(f" - [I] Joern server starting [port={self.__port}] [memory={self.__memory}]", flush=True)
            cmd = [self.joern, "--server", "--server-port", f"{self.__port}", "--nocolors"]
            env = self.env.copy()
            env["JAVA_OPTS"] = f"-Xmx{self.__memory}G -XX:ParallelGCThreads=8 -XX:ConcGCThreads=4 -Djava.util.concurrent.ForkJoinPool.common.parallelism=20"
            self.__server = subprocess.Popen(
                cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            retry = 60
            while retry > 0:
                try:
                    res = self.query("", restart_on_failure=False)[0]
                    if (
                        isinstance(res, dict)
                        and "success" in res
                        and res["success"] == True
                    ):
                        print(" - [I] Joern server started", flush=True)
                        return
                except Exception:
                    pass
                retry -= 1
                time.sleep(1)
            print(" - [E] Failed to start joern server", flush=True)
            self.stop()

        if self.is_running():
            self.stop()

        self.__port = __assign_port()
        self.__url = f"http://localhost:{self.__port}/query-sync"
        __run()
        try:
            for n, init_script in enumerate(self.__init_scripts):
                try:
                    self.query(
                        init_script,
                        timeout=self.__init_timeout,
                        restart_on_failure=False,
                    )
                except Exception:
                    print(f" - [W] Joern server failed init script{n}", flush=True)
        except Exception:
            print(f" - [W] Joern server failed init script", flush=True)
