from vuli.common.singleton import Singleton
import functools
import os
import shutil


class Setting(metaclass=Singleton):
    # Common
    harnesses: list[str] = []
    reuse: bool = True

    # CP
    cp_dir: str = None

    # Joern
    joern_dir: str = None
    query_path: str = None
    semantic_path: str = None
    joern_timeout: int = 30

    # LLM
    n_response: int = 10
    temperature: float = 1.0
    num_retries: int = 3
    budget: float = 0.0
    limit: int = 0

    # Output
    output_dir: str = "output"
    blackboard_path: str = os.path.join(output_dir, "blackboard")
    cpg_path: str = None

    # Tool
    python_path: str = None

    def set_llm_parameter(
        self, n_response: int, temperature: float, budget: int, limit: int
    ) -> None:
        self.n_response = n_response
        self.budget = budget
        self.limit = limit

        if temperature < 0.0:
            temperature = 0.0
        if temperature > 2.0:
            temperature = 2.0
        self.temperature = temperature

    def set_output_dir(self, output_dir: str) -> None:
        self.output_dir = output_dir
        if os.path.isfile(self.output_dir):
            os.remove(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.blackboard_path = os.path.join(self.output_dir, "blackboard")
        self.cpg_path = os.path.join(self.output_dir, "cpg")

    def set_python_path(self, python_path: str = None) -> None:
        if (python_path != None) and (shutil.which(python_path) != None):
            self.python_path = python_path
        else:
            for python_path_candidate in ["python3", "python"]:
                if shutil.which(python_path_candidate) == None:
                    continue
                self.python_path = python_path_candidate
                break

        if self.python_path == None:
            raise RuntimeError("Fail to set python path")

    def set_root_dir(self, root_dir: str) -> None:
        self.root_dir = root_dir
        self.query_path = os.path.join(root_dir, "script", "script.sc")
        self.semantic_dir = os.path.join(root_dir, "script", "semantics")

    def __str__(self):
        result = ""

        result += f"Common Setting:\n"
        result += f"harnesses: {self.harnesses}\n"
        result += f"reuse: {self.reuse}\n"

        result += f"\n"

        result += f"CP Setting:\n"
        result += f"cp_dir: {self.cp_dir}\n"

        result += f"\n"

        result += f"Joern Setting:\n"
        result += f"cpg_path: {self.cpg_path}\n"
        result += f"query_path: {self.query_path}\n"
        result += f"semantic_dir: {self.semantic_dir}\n"
        result += f"joern_timeout: {self.joern_timeout}\n"

        result += f"\n"

        result += f"LLM Setting:\n"
        result += f"n_response: {self.n_response}\n"
        result += f"temperature: {self.temperature}\n"
        result += f"num_retries: {self.num_retries}\n"
        result += f"budget: {self.budget}\n"
        result += f"limit: {self.limit}\n"

        result += f"\n"

        result += f"Output Setting:\n"
        result += f"output_dir: {self.output_dir}\n"
        result += f"blackboard_path: {self.blackboard_path}\n"

        result += f"\n"
        result += f"Tool Setting:\n"
        result += f"python_path: {self.python_path}\n"

        return result
