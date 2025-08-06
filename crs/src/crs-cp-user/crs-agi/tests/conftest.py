from collections import namedtuple

import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--replay", action="store", default=None, help="enable replaying of LLM completions (path)"
    )
    parser.addoption(
        "--record", action="store", default=None, help="enable recording of LLM completions (path)"
    )
    parser.addoption(
        "--seed", action="store", default=None, type=int, help="seed for completion selection"
    )
    parser.addoption(
        "--keep", action="store_true", default=False, help="keep the workspace directory"
    )
    parser.addoption(
        "--model", action="store", default="gpt-4o", help="llm model (e.g., gpt-4o, gemini-1.5-pro)"
    )

Opts = namedtuple("Opts", "record replay seed delete model")

@pytest.fixture
def opts(request):
    o = Opts(
        record=request.config.getoption("--record"),
        replay=request.config.getoption("--replay"),
        seed=request.config.getoption("--seed"),
        delete=not request.config.getoption("--keep"),
        model=request.config.getoption("--model"),
    )
    assert o.record is None or o.replay is None
    return o
