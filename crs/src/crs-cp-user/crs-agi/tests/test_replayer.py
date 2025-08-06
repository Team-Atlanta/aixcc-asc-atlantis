import pytest
import tempfile
import os

from llm.models import Prompt, LLM
from llm.replayer import Recorder, Replayer
from llm.plugins import ExecutePython, Workspace

import rich


@pytest.fixture
def workspace():
    return Workspace(delete=True)

@pytest.fixture
def pyplugin(workspace):
    return ExecutePython(workspace=workspace)


def test_rr_sanity_check(pyplugin):
    p = Prompt()
    r = Recorder()
    gpt = LLM.setup("gpt-4o", plugins=[pyplugin])

    p.append("print 'hello world' by using `execute_python()`")
    r.add(gpt, p.get()[-1], "hello")

    p.append("print 'world' by using `execute_python()`")
    r.add(gpt, p.get()[-1], "world")

    (_, tmp) = tempfile.mkstemp(".json")
    r.save_to(tmp)

    p = Prompt()
    r = Replayer(tmp)

    gpt = LLM.setup("gpt-4o", plugins=[pyplugin])

    lasthash = None

    p.append("print 'hello world' by using `execute_python()`")
    (lasthash, completion) = r.get(gpt, lasthash, p.get()[-1])

    assert lasthash
    assert completion == "hello"

    p.append("print 'world' by using `execute_python()`")
    (lasthash, completion) = r.get(gpt, lasthash, p.get()[-1])

    assert lasthash
    assert completion == "world"

    os.unlink(tmp)

def test_rr_simple(pyplugin):
    recorder = Recorder()
    prompt = Prompt()
    prompt.append("print 'hello world' by using `execute_python()`")

    gpt = LLM.setup("gpt-4o", plugins=[pyplugin], recorder=recorder)
    gpt.run(prompt)

    (_, tmp) = tempfile.mkstemp(".json")
    recorder.save_to(tmp)

    assert "hello world" in prompt.get()[-1]["content"]

    replayer = Replayer(tmp)
    prompt = Prompt()
    prompt.append("print 'hello world' by using `execute_python()`")

    gpt = LLM.setup("gpt-4o", plugins=[pyplugin], replayer=replayer)
    gpt.run(prompt)

    assert "hello world" in prompt.get()[-1]["content"]
