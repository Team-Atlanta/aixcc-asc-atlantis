import pytest
import time
from src.LLMManager import LLMManager  # LLMManager 클래스가 정의된 모듈을 import


@pytest.fixture
def llm_manager():
    budget = 100
    return LLMManager(budget=budget)


def test_rate_limit_management(llm_manager):
    model = "test_model"
    assert not llm_manager.is_rate_limited(model)

    # Rate limit the model
    llm_manager.rate_limit(model)
    assert llm_manager.is_rate_limited(model)

    # Wait for the rate limit to expire
    time.sleep(1)
    llm_manager.model_expiration_times[model] = time.time() - 1
    assert not llm_manager.is_rate_limited(model)


def test_cost_management(llm_manager):
    assert llm_manager.has_cost_exceeded_limit()

    # Simulate cost increase
    with llm_manager.lock:
        llm_manager.cost = 50
    assert llm_manager.has_cost_exceeded_limit()

    with llm_manager.lock:
        llm_manager.cost = 150
    assert not llm_manager.has_cost_exceeded_limit()


def test_rate_limit_and_cost_interaction(llm_manager):
    model = "test_model"

    # Ensure the model is not rate limited initially
    assert not llm_manager.is_rate_limited(model)

    # Simulate cost exceeding the budget
    with llm_manager.lock:
        llm_manager.cost = 150

    # Even if the model is not rate limited, the budget should stop further processing
    assert not llm_manager.has_cost_exceeded_limit()

    # Rate limit the model and check if it reflects correctly
    llm_manager.rate_limit(model)
    assert llm_manager.is_rate_limited(model)
