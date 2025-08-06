import os
import argparse
import litellm
import shutil

from glob import glob
from abc import abstractmethod
from pathlib import Path
from collections import namedtuple

import rich
from loguru import logger

from llm.models import LLM
from llm.plugins import (ExecutePython, ExecuteShell, Workspace, WorkspaceTool,
    get_workspace_plugins, get_mentalcare_plugins, )
from llm.replayer import Replayer, Recorder
from llm.repo import RepoWorkspace
from llm.prompt import Prompt, load_prompt
from llm.errors import PluginSuccess, PluginErrorGivingUp, PluginErrorRetry
from llm.runner import LLMRunner
from llm.util import md5sum

ROOT = Path(os.path.dirname(__file__))


def cp_root(cp):
    return (ROOT / "../cp_root" / cp).resolve()


def get_llm(opts, plugins=None):
    recorder = Recorder(opts.record) if opts.record else None
    replayer = Replayer(opts.replay, seed=opts.seed) if opts.replay else None

    return LLM.setup(opts.model,
                     plugins=plugins,
                     temperature=opts.temperature,
                     replayer=replayer,
                     recorder=recorder)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, help="a root path to the code repo", required=True)
    parser.add_argument("--delete", action="store_true", help="delete the workspace on exit", default=False)
    parser.add_argument("--workspace", type=Path, help="(re-)use the specified workspace", default=None)
    parser.add_argument("--temperature", type=float, help="Temperature for LLM", default=None)
    parser.add_argument("--replay", type=Path, help="Replay the session", default=None)
    parser.add_argument("--record", type=Path, help="Record the session", default=None)
    parser.add_argument("--seed", help="Random seed for llm", nargs='?', const=1, type=int)
    parser.add_argument("--no-rebuild", action="store_true", help="Don't reset/build the CP from scratch", default=False)
    parser.add_argument("--model", help="Specify the llm model (e.g., gpt-4o, gemini-1.5-pro)", default="oai-gpt-4o")
    parser.add_argument("--debug", action="store_true", help="Print out VERY VERBOSE messages (litellm)", default=False)
    parser.add_argument("--show-repomap", action="store_true", help="Show a repomap (aider)", default=False)
    parser.add_argument("--out", help="Where to copy the dictionary to (if successful)", default=None)

    args = parser.parse_args()
    args.repo = args.repo.resolve()

    assert args.repo.exists()

    if args.debug:
        litellm.set_verbose = True

    return args


class SaveDictPlugin(WorkspaceTool):
    name = "save_dict"
    description = """\
Save the generated dictionary. It should be called to inform a user about the generated dictionary before terminating the session."""
    params =  {
        "type": "object",
        "properties": {
            "dictionary": {
                "type": "string",
                "description": "A content of the dictionary file for the libfuzzer."},
        },
        "required": ["dictionary"]
    }

    @abstractmethod
    def run(self, **args):
        if not "dictionary" in args:
            return

        out = self.workspace.get_dict_path()
        self.workspace.log(f"SAVE {out}")
        with open(out, "w") as fd:
            fd.write(args["dictionary"])

class GetFilePlugin(WorkspaceTool):
    name = "get_file"
    description = """\
Read the content of the file."""
    params =  {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Read the content of the file in the repo."},
        },
        "required": ["dictionary"]
    }

    @abstractmethod
    def run(self, **args):
        if not "name" in args:
            return "N/A"

        out = self.workspace.repo / args["name"]
        if out.exists():
            return out.read_text()
        else:
            return "N/A"


class GetDictPlugin(WorkspaceTool):
    name = "get_dict"
    description = """\
Get the sample dictionary."""
    params =  {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "A name of the sample libfuzzer dictionary."},
        },
        "required": ["name"]
    }

    @abstractmethod
    def run(self, **args):
        if not "name" in args:
            return

        return self.workspace.read(workspace.dict_dir / args["name"])


class DictOracle:
    name = "dict"

    def check(self, runner):
        workspace = runner.workspace
        return workspace.get_dict_path().exists()


if __name__ == "__main__":
    args = parse_args()

    workspace = RepoWorkspace(repo=args.repo,
                              root=args.workspace,
                              delete=args.delete)


    repomap = workspace.build_repomap()
    if args.show_repomap:
        print(repomap)
        exit(0)

    readme = []
    for pn in glob(str(workspace.repo / "README*")):
        readme.append(Path(pn).read_text())
    readme = "\n".join(readme)

    if len(readme) == 0:
        readme = None

    # TODO. tools:
    #
    #  get_file()
    #  get_dict()
    #  save_dict()
    #
    packages = ["numpy", "tree-sitter", "standard libs"]
    plugins = [
        ExecutePython(workspace, packages=packages),
        ExecuteShell(workspace),
        get_workspace_plugins(workspace),
        get_mentalcare_plugins(workspace),
        SaveDictPlugin(workspace),
        GetFilePlugin(workspace)
    ]

    prompt = Prompt()
    prompt.append(load_prompt("aixcc-crs.txt"), role="system")
    prompt.append(load_prompt("fuzzdict-background.txt"))
    prompt.append(load_prompt("fuzzdict-context.txt",
                              readme=readme,
                              repomap=repomap,
                              dictionaries="N/A"))

    llm = get_llm(args, plugins=plugins)

    # What's a reasolable timeout? NGINX took 90s
    runner = LLMRunner(args, llm, prompt, workspace, oracles=[DictOracle()], timeout=300)

    (state, oracles) = runner.run()
    print(oracles)

    pn = workspace.get_dict_path()
    if pn.exists():
        logger.info("Generated dict:")
        logger.info(pn.read_text())

    if pn.exists() and args.out:
        logger.info(f"Dictionary: @{args.out}")
        shutil.copy(pn, args.out)
