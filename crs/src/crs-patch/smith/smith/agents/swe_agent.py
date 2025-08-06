from contextlib import contextmanager
from pathlib import Path
import os
import sys
import tempfile
from typing import Dict
from typing_extensions import override

from git import Repo

from smith.bug import Bug
from smith.model import (
    Dialog,
    Model,
    get_available_models
)
# Importing as BaseAgent due to collision with import from swe_agent
from smith.agents.base_agent import Agent as BaseAgent

sys.path.append(str(Path(__file__).parent.parent / "lib" / "swe_agent"))

# pylint: disable=wrong-import-position
from smith.lib.swe_agent.sweagent import (
    Agent,
    AgentArguments,
    ModelArguments,
    EnvironmentArguments,
    SWEEnv
)
# pylint: enable=wrong-import-position

@contextmanager
def chdir(path: Path):
    current_dir = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(current_dir)


class SWEAgent(BaseAgent):
    SWE_AGENT_DIR = Path(__file__).parent.parent / "lib" / "swe_agent"

    @override
    @staticmethod
    def name() -> str:
        return "SWEAgent"

    @override
    def __init__(self, model: Model, bug: Bug, temperature: float):
        # chdir is necessary because command_files of config/default.yaml are relative paths
        with chdir(self.SWE_AGENT_DIR):
            # Create "keys.cfg" file
            with open("keys.cfg", "w") as f:
                f.write(f"OPENAI_API_KEY: '{os.environ['LITELLM_KEY']}'\n")
                f.write(f"OPENAI_API_BASE_URL: '{os.environ['AIXCC_LITELLM_HOSTNAME']}'\n")

            self._agent = Agent(
                "primary",
                AgentArguments(
                    model=ModelArguments(
                        model_name=self.model_converter()[model.name()],
                        total_cost_limit=0.0,
                        per_instance_cost_limit=1.0,
                        temperature=temperature,
                        top_p=0.95,
                    ),
                    config_file=self.SWE_AGENT_DIR / "config/default.yaml",
                )
            )
        self._repo = Repo(bug.challenge.src_dir, search_parent_directories=True)
        self._patch:str = ""

        self._image_name = self._get_image_name()

    def _get_image_name(self) -> str:
        if Path("/.dockerenv").exists() or "IN_DOCKER_CONTAINER" in os.environ:
            # Running inside a docker container
            return "none"
        else:
            return "sweagent/swe-agent:latest"

    @override
    def query(self, message: str) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as f:
            f.write(message)
            f.flush()

            env = SWEEnv(
                EnvironmentArguments(
                    image_name=self._image_name,
                    repo_path=str(self._repo.working_dir),
                    base_commit=self._repo.head.commit.hexsha,
                    data_path=f.name,
                    install_environment=False,
                )
            )

        env.reset()
        # chdir is necessary because command_files of config/default.yaml are relative paths
        with chdir(self.SWE_AGENT_DIR):
            info = self._agent.run(
                setup_args={"issue": env.query},
                env=env,
                return_type="info",
            )

        self._patch = info.get("submission")

    @override
    def get_patch_diff(self) -> str:
        if self._patch is not None:
            return self._patch

        return ""

    @override
    def get_dialogs(self) -> Dialog:
        return Dialog(self._agent.history)

    @override
    def model_converter(self) -> Dict[str,str]:
        return {
            model_name: model_name for model_name in get_available_models()
        }
