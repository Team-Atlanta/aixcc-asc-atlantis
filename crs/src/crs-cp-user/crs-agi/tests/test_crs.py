import pytest
import json
import os
import shutil
import rich

from pathlib import Path

from llm.models import Prompt, LLM
from llm.plugins import (
    ExecutePython, ExecuteShell, Workspace,
    get_workspace_plugins,
    get_mentalcare_plugins,
)
from llm.replayer import Replayer, Recorder
from llm.crs import CRSWorkspace, get_crs_plugins
from llm.errors import PluginErrorGivingUp, PluginErrorRetry, PluginSuccess

ROOT = Path(os.path.dirname(__file__))

def cp_root(cp):
    return (ROOT / "../cp_root" / cp).resolve()


def get_llm(opts, plugins=None, temperature=None):
    recorder = Recorder(opts.record) if opts.record else None
    replayer = Replayer(opts.replay, seed=opts.seed) if opts.replay else None

    return LLM.setup("gpt-4o",
                     plugins=plugins,
                     temperature=temperature,
                     replayer=replayer,
                     recorder=recorder)

def test_plugin_sanity_checks(opts):
    workspace = Workspace(delete=True)

    mockcp = cp_root("mock-cp")
    workspace.ln(mockcp, "cp")

    # sample runs
    assert workspace.run("ls")
    assert workspace.run("make", cwd="cp")
    assert workspace.run("make pre-check", cwd="cp", shell=True)
    assert workspace.run("./run.sh; exit 0", cwd="cp", shell=True)
    assert workspace.run(["./run.sh", "build"], cwd="cp")
    assert workspace.run(["./run.sh", "run_tests"], cwd="cp")
    assert not workspace.run("no-such-a-file")


def test_analyzing_test_harness(opts):
    cp = cp_root("mock-cp")
    workspace = CRSWorkspace(cp, delete=False)

    output = cp / "out/output"
    if output.exists():
        shutil.rmtree(output)
        os.mkdir(output)

    plugins = [
        ExecutePython(workspace),
        ExecuteShell(workspace),
        get_workspace_plugins(workspace),
        get_crs_plugins(workspace),
        get_mentalcare_plugins(workspace)
    ]

    prompt = Prompt()
    prompt.append("You are an autonomous agent. You are brilliant, and tireless working. "
                  "Your goal is to recognize blob files for testing "
                  "and the name of testing harness."
                  "To check if the found blob file and harness working, you can verify it with "
                  "`run.sh run_pov <blob_file> <harness_name>`."
                  "You might want to check a project description file at `project.yaml`, "
                  "and the testing script, `run.sh`. "
                  "The testing can be run with `run.sh run_tests`.\n\n"
                  "Your job is to list up <blob_file> and <harness_name> that properly work with `run.sh run_pov`!")

    gpt = get_llm(opts, plugins=plugins)
    for _ in range(20):
        try:
            gpt.run(prompt)
        except PluginSuccess as e:
            summary = e.summary
            break
        except Exception as e:
            rich.inspect(prompt.get()[-3:])
            raise e

    prompt.store_to(workspace.history / "chat.json")

    assert "test/test1.blob" in summary
    assert "test/test2.blob" in summary
    assert "stdin_harness.sh" in summary

