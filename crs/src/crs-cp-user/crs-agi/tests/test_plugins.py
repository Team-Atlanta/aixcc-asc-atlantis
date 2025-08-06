import pytest

import rich
import time

from llm.models import Prompt, LLM
from llm.plugins import ExecutePython, ExecuteShell, Workspace, get_workspace_plugins, get_mentalcare_plugins
from llm.replayer import Replayer, Recorder
from llm.errors import PluginErrorGivingUp, PluginErrorRetry, PluginErrorTimeout


@pytest.fixture
def workspace(opts):
    return Workspace(delete=opts.delete)

@pytest.fixture
def pyplugin(workspace):
    return ExecutePython(workspace=workspace)

@pytest.fixture
def shplugin(workspace):
    return ExecuteShell(workspace=workspace)

@pytest.fixture
def prompt():
    return Prompt()


def get_llm(opts, plugins=None, temperature=None):
    recorder = Recorder(opts.record) if opts.record else None
    replayer = Replayer(opts.replay, seed=opts.seed) if opts.replay else None

    return LLM.setup(opts.model,
                     plugins=plugins,
                     temperature=temperature,
                     replayer=replayer,
                     recorder=recorder)

def test_plugin_basic(pyplugin, prompt, opts):
    prompt.append("print 'hello world' by using `execute_python()`")

    gpt = get_llm(opts, [pyplugin])
    rtn = gpt.query(prompt)

    assert len(rtn.choices[0].message.tool_calls) != 0
    assert rtn.choices[0].message.tool_calls[0].function.name == "execute_python"


def test_plugin_sanity(pyplugin):
    assert "hello\n" == pyplugin.run("print('hello')")[0]
    assert "" == pyplugin.run("def test_me(arg):\n    print(arg)\n")[0]
    assert "NameError" in pyplugin.run("test_me('world!')")[1]
    assert "world!\n" in pyplugin.run("def test_me(arg):\n    print(arg)\n\ntest_me('world!')")[0]

    # if it ends with expr, print() explicitly
    assert "hey!\n" in pyplugin.run("v='hey!'\nv")[0]


def test_plugin_tool_basic(pyplugin, prompt, opts):
    prompt.append("print 'hello world' two times by invoking `execute_python()` two times!")

    gpt = get_llm(opts, [pyplugin])
    rtn = gpt.run(prompt)

    rich.inspect(prompt.get())

    assert len(list(filter(lambda e: e.get("tool_call_id", False), prompt.get()))) == 2


def test_plugin_using_tool(pyplugin, prompt, workspace, opts):
    prompt.append("write a python code that gets the tmp directory from `tools.tmpdir()`. Use `execute_python()`.")

    gpt = get_llm(opts, [pyplugin])
    gpt.run(prompt)

    assert str(workspace.tmp) in prompt.get()[-1]["content"]

    rich.inspect(prompt.get())


def test_plugin_complex_python_task(pyplugin, prompt, workspace, opts):
    prompt.append("""\
    You are an autonomous agent that thinks, plans, acts by using the Python programming language. \
    Express what you have to do in the Python code and \
    carefully execute it by using `execute_python()`. \
    The code will be executed in a user's machine and persists only in this session.\
""",
                  role="system")

    prompt.append("""\
You task is to write a Fibonacci function and store it as a file (`fib.py`) under a directory (`tools.tmpdir()`).
""")

    gpt = get_llm(opts, [pyplugin])
    gpt.run(prompt)

    prompt.append("Test if `fib.py` runs correctly and provides a list of tests. Use `tools.tmpdir()` instead of an absolute path.")
    gpt.run(prompt)

    # check if `fib.py` is created properly
    assert (workspace.tmp / "fib.py").exists()

    rich.inspect(prompt.get())


def test_plugin_using_sh_py(pyplugin, shplugin, workspace, prompt, opts):
    plugins = [pyplugin, shplugin] + get_workspace_plugins(workspace)

    prompt.append("""
    Create a file with a random name under a directory is specified by `tools.tmpdir()`.
    Write a python code to the file that prints "hello world".""")

    gpt = get_llm(opts, plugins=plugins, temperature=0.2)
    gpt.run(prompt)

    prompt.append("List the files in the tmp directory and figure out the name of the stored file.")
    gpt.run(prompt)

    prompt.append("Execute the discovered file!")
    gpt.run(prompt)

    assert "hello world" in prompt.get()[-1]["content"].lower()


def test_plugin_giving_up(opts):
    workspace = Workspace(delete=True)

    plugins = [
        ExecutePython(workspace),
        ExecuteShell(workspace),
        get_workspace_plugins(workspace),
        get_mentalcare_plugins(workspace)
    ]

    prompt = Prompt()
    prompt.append("""You are a programmer. Give up if you don't know how to do (i.e., calling `session_giving_up()`)""", 
                  role="system")
    prompt.append("Prove that the P solution exists for TSP, and show its implementation.")

    gpt = get_llm(opts, plugins=plugins)
    givingup = False
    for i in range(10):
        try:
            gpt.run(prompt)
            prompt.append("It's not the P solution! Prove it.")
        except PluginErrorGivingUp as e:
            givingup = True
            break

    prompt.store_to(workspace.history / "chat.json")

    assert givingup


def test_plugin_timeout(opts):
    workspace = Workspace(delete=True)

    plugins = [
        ExecutePython(workspace),
        ExecuteShell(workspace),
        get_workspace_plugins(workspace),
        get_mentalcare_plugins(workspace)
    ]

    prompt = Prompt()
    prompt.append("""You are a programmer. Try hard!""", role="system")
    prompt.append("Calculate fib(1000000). Try it with `timeout` = 1 sec.")

    gpt = get_llm(opts, plugins=plugins)

    for _ in range(3):
        try:
            gpt.run(prompt)
        except PluginErrorGivingUp as e:
            prompt.append("I know, but TRY!")

    prompt.store_to(workspace.history / "chat.json")

    found = False
    for p in prompt.get():
        if "tool_call_id" in p:
            if "timeout:" in p["content"]:
                found = True
                break
    rich.inspect(prompt.get())

    assert found
