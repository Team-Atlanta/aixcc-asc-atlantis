# pylint: disable=wrong-import-position
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from functools import wraps
from typing import List, Any, Type, Dict, Callable
import os
import time
import json
import warnings # type: ignore

warnings.filterwarnings("ignore")

from typing_extensions import override
from openai import RateLimitError
# TODO: `import litellm` produces warnings (PydanticDeprecatedSince20, UserWarning, etc...)
import litellm # type: ignore

from . import constants
from .plugin import Plugin

l = logging.getLogger(__name__)

class MaxRetryError(Exception):
    pass

def _repeat_until_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        trial = 0
        while trial < constants.MAX_RETRY_COUNT_FOR_RATE_LIMIT_ERROR:
            try:
                return func(*args, **kwargs)
            except RateLimitError:
                time.sleep(30)
                trial += 1
        raise MaxRetryError('Max retry count reached for RateLimitError.')
    return wrapper

class Dialog:
    def __init__(self, messages: List[dict]):
        self._messages = messages

    def to_raw(self) -> Any:
        return self._messages

    def add_assistant_message(self, msg: str) -> Dialog:
        return Dialog(self._messages + [{"role": "assistant", "content": msg}])

    def add_user_message(self, msg: str) -> Dialog:
        return Dialog(self._messages + [{"role": "user", "content": msg}])

    @property
    def round(self) -> int:
        # The round number is the number of assistant messages + 1
        return len([item for item in self._messages if item["role"] == "assistant"]) + 1

class Model(ABC):
    def __init__(self, use_plugins: bool = False) -> None:
        if "LITELLM_KEY" not in os.environ:
            raise ValueError("LITELLM_KEY is not set")

        self._use_plugins = use_plugins
        self._plugins: List[Dict] = []
        self._plugin_handlers: Dict[str, Callable] = {}

    @property
    def use_plugins(self) -> bool:
        return self._use_plugins

    def install_plugin(self, plugin: Plugin) -> None:
        self._plugins.append(plugin.spec)
        self._plugin_handlers[plugin.name] = plugin.handler

    def install_plugins(self, plugins: List[Plugin]) -> None:
        for plugin in plugins:
            self.install_plugin(plugin)

    def query(self, dialog: Dialog, num_samples: int) -> List[str]:
        if self._use_plugins and self.supports_function_calling:
            return self._query_with_plugins(dialog, num_samples)
        else:
            return self._query(dialog, num_samples)

    @_repeat_until_limit
    def _query(self, dialog: Dialog, num_samples: int) -> List[str]:
        kwargs = self._build_kwargs(dialog.to_raw(), num_samples=num_samples)
        response = litellm.completion(**kwargs)

        # completion API should return ModelResponse
        assert isinstance(response, litellm.ModelResponse)
        return [choice.message.content for choice in response.choices]

    def _build_kwargs(self, message, num_samples=1, with_plugins=False) -> Dict[str, Any]:
        kwargs = {
            "model": self.name(),
            "base_url": os.environ["AIXCC_LITELLM_HOSTNAME"],
            "api_key": os.environ["LITELLM_KEY"],
            "messages": message,
            "temperature": 1,
            "top_p": 1,
            "n": num_samples,
            "max_tokens": self.max_tokens,
            "custom_llm_provider": "openai",
        }

        if with_plugins and len(self._plugins) != 0:
            kwargs["tools"] = self._plugins
            kwargs["tool_choice"] = "auto"

        return kwargs

    @_repeat_until_limit
    def _query_single_with_plugins(self, messages) -> str:
        l.info("Entering _query_single_with_plugins")
        while True:
            kwargs = self._build_kwargs(messages, with_plugins=True)
            completion = litellm.completion(**kwargs)
            response = completion.choices[0].message
            messages.append(response)

            if not hasattr(response, "tool_calls"):
                return response.content

            tool_calls = response.tool_calls
            self._apply_tool_calls(messages, tool_calls)

    def _apply_tool_calls(self, messages, tool_calls):
        for call in tool_calls:
            function_name = call.function.name
            handler = self._plugin_handlers[function_name]
            args = json.loads(call.function.arguments)
            function_response = handler(**args)
            messages.append(
                {
                    "tool_call_id": call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response
                }
            )

    def _query_with_plugins(self, dialog: Dialog, num_samples: int) -> List[str]:
        responses = []
        for _ in range(num_samples):
            try:
                responses.append(self._query_single_with_plugins(dialog.to_raw()))
            except MaxRetryError:
                continue
        return responses

    def initiate_dialog(self, content: str) -> Dialog:
        return Dialog([
            {"role": "system", "content": content},
        ])

    @staticmethod
    @abstractmethod
    def name() -> str:
        pass

    @property
    @abstractmethod
    def context_window(self) -> int:
        pass

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        pass

    @property
    @abstractmethod
    def supports_function_calling(self) -> bool:
        pass

class GPT35(Model):
    @override
    @staticmethod
    def name() -> str:
        return "oai-gpt-3.5-turbo"

    @override
    @property
    def context_window(self) -> int:
        return 16385

    @override
    @property
    def max_tokens(self) -> int:
        return 4096

    @override
    @property
    def supports_function_calling(self) -> bool:
        return True

class GPT4(Model):
    @override
    @staticmethod
    def name() -> str:
        return "oai-gpt-4-turbo"

    @override
    @property
    def context_window(self) -> int:
        return 128000

    @override
    @property
    def max_tokens(self) -> int:
        return 4096

    @override
    @property
    def supports_function_calling(self) -> bool:
        return True

class GPT4o(Model):
    @override
    @staticmethod
    def name() -> str:
        return "oai-gpt-4o"

    @override
    @property
    def context_window(self) -> int:
        return 128000

    @override
    @property
    def max_tokens(self) -> int:
        return 4096

    @override
    @property
    def supports_function_calling(self) -> bool:
        return True

class GeminiPro(Model):
    @override
    @staticmethod
    def name() -> str:
        return "gemini-1.5-pro"

    @override
    @property
    def context_window(self) -> int:
        return 1000000

    @override
    @property
    def max_tokens(self) -> int:
        return 8192

    @override
    @property
    def supports_function_calling(self) -> bool:
        # TODO: fix it
        return False

class Claude3Model(Model):
    """Cannot use n and tools in kwargs."""
    @override
    @_repeat_until_limit
    def _query(self, dialog: Dialog, num_samples: int) -> List[str]:
        kwargs = self._build_kwargs(dialog.to_raw())
        return [
            response.choices[0].message.content for _ in range(num_samples)
            if isinstance((response := litellm.completion(**kwargs)), litellm.ModelResponse)
        ]

    @override
    def _build_kwargs(self, message, _num_samples=1, _with_plugins=False) -> Dict[str, Any]:
        kwargs = {
            "model": self.name(),
            "base_url": os.environ["AIXCC_LITELLM_HOSTNAME"],
            "api_key": os.environ["LITELLM_KEY"],
            "messages": message,
            "temperature": 1,
            "top_p": 1,
            "max_tokens": self.max_tokens,
            "custom_llm_provider": "openai",
        }

        return kwargs

    @override
    def _query_with_plugins(self, dialog: Dialog, num_samples: int) -> List[str]:
        # TODO: Raise exception
        return []

    @override
    @property
    def context_window(self) -> int:
        return 200000

    @override
    @property
    def max_tokens(self) -> int:
        return 4000

    @override
    @property
    def supports_function_calling(self) -> bool:
        return True

class Claude3Haiku(Claude3Model):
    @override
    @staticmethod
    def name() -> str:
        return "claude-3-haiku"

class Claude3Sonnet(Claude3Model):
    @override
    @staticmethod
    def name() -> str:
        return "claude-3-sonnet"

class Claude3Opus(Claude3Model):
    @override
    @staticmethod
    def name() -> str:
        return "claude-3-opus"

class Claude35Sonnet(Claude3Model):
    @override
    @staticmethod
    def name() -> str:
        return "claude-3.5-sonnet"

### Utility functions

AVAILBLE_MODELS: List[Type[Model]] =  [
    GPT35, GPT4, GPT4o, GeminiPro, Claude3Haiku, Claude3Sonnet, Claude3Opus, Claude35Sonnet
]

def get_available_models() -> List[str]:
    return [model.name() for model in AVAILBLE_MODELS]

def get_model(name: str) -> Type[Model]:
    for model in AVAILBLE_MODELS:
        if model.name() == name:
            return model

    raise ValueError(f'invalid model: {name}')
