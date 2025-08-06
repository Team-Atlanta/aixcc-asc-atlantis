import pytest
from unittest.mock import MagicMock
from src.chat import OpenAIChat
from src.LLMManager import LLMManager
from src.completion import OpenAICompletion


@pytest.fixture
def completion():
    return MagicMock(OpenAICompletion)


@pytest.fixture
def llm_manager():
    return LLMManager(budget=20)


def test_complete_binary_class(completion, llm_manager):
    bug_type = ["test_bug"]
    commit_id = "commit123"
    func_changes = [
        "main",
    ]

    completion.create.side_effect = [("vulnerable", 1.0)]
    completion.parse_response.side_effect = ["vulnerable"]

    chat = OpenAIChat(bug_type)
    result = chat.complete(commit_id, func_changes, completion, llm_manager)

    assert result == (commit_id, "vulnerable", 1.0, "test_bug", "main")


def test_complete_invalid_binary_class(completion, llm_manager):
    bug_type = []
    commit_id = "commit123"
    func_changes = ["main"]

    completion.create.side_effect = [("vulnerable", 1.0)]
    completion.parse_response.side_effect = ["vulnerable"]

    chat = OpenAIChat(bug_type)
    result = chat.complete(commit_id, func_changes, completion, llm_manager)

    assert result == (commit_id, "invalid", 1.0, "None", "")


def test_complete_success_multi_class(completion, llm_manager):
    bug_type = ["test_bug"]
    commit_id = "commit123"
    func_changes = ["main", "main2"]

    completion.create.side_effect = [("response1", 1.0), ("main", 1.0)]
    completion.parse_response.side_effect = ["test_bug", "main"]

    chat = OpenAIChat(bug_type)
    result = chat.complete(commit_id, func_changes, completion, llm_manager)

    assert result == (commit_id, "test_bug", 2.0, "test_bug", "main")


def test_complete_invalid_response(completion, llm_manager):
    bug_type = ["test_bug"]
    commit_id = "commit123"
    func_changes = ["main", "main2"]

    def create_side_effect():
        responses = [("response1", 1.0), ("test_bug", 1.0), ("main", 1.0)]
        for response in responses:
            yield response

    completion.create.side_effect = create_side_effect()
    completion.parse_response.side_effect = ["invalid", "test_bug", "main"]

    chat = OpenAIChat(bug_type)
    result = chat.complete(commit_id, func_changes, completion, llm_manager)

    assert completion.continue_chat.call_count == 2
    assert result == (commit_id, "test_bug", 3.0, "test_bug", "main")


def test_complete_exceed_case(completion, llm_manager):
    bug_type = ["test_bug", "test2"]
    commit_id = "commit123"
    func_changes = []

    completion.create.side_effect = [("exceed", 0.0)]
    completion.parse_response.side_effect = ["exceed"]

    chat = OpenAIChat(bug_type)
    result = chat.complete(commit_id, func_changes, completion, llm_manager)

    assert result == (commit_id, "invalid", 0.0, "invalid", "")


def test_complete_error_case(completion, llm_manager):
    bug_type = ["test_bug", "test2"]
    commit_id = "commit123"
    func_changes = []

    completion.create.side_effect = [("error", 1.0)]
    completion.parse_response.side_effect = ["error"]

    chat = OpenAIChat(bug_type)
    result = chat.complete(commit_id, func_changes, completion, llm_manager)

    assert result == (commit_id, "invalid", 1.0, "invalid", "")
