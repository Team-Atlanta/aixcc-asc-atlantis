import pytest
from src.model import GPT4o


@pytest.fixture
def gpt4o():
    return GPT4o()


def test_gpt4o_properties(gpt4o):
    assert gpt4o.name == "oai-gpt-4o"
    assert gpt4o.context_window == 128000
    assert gpt4o.max_tokens == 4096
    assert gpt4o.supports_function_calling
    assert gpt4o.provider == "openai"
