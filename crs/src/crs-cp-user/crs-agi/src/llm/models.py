#!/usr/bin/env python3

import json
import os

import tiktoken
import openai

from loguru import logger

from rich.console import Console
from rich.syntax import Syntax

from .prompt import Prompt
from .errors import PluginErrorGivingUp, PluginErrorRetry, PluginErrorTimeout, PluginSuccess

DEFAULT_TEMPERATURE: float = 0.4

LITELLM_URL = os.getenv("LITELLM_URL", None)
LITELLM_KEY = os.getenv("LITELLM_KEY", None)

logger.info(f"LITELLM_URL: {LITELLM_URL}")

def prettyprint_code(lang, code):
    syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
    console = Console()
    console.print(syntax)


class LLM:
    """Base LLM."""

    name: str
    max_tokens: int
    temperature: float

    def __init__(
        self,
        max_tokens=None,
        temperature=None,
        seed=None,
        json_mode=False,
        plugins=None,
        recorder=None,
        replayer=None
    ):
        # overwrite default hyperparams
        if max_tokens:
            self.max_tokens = max_tokens

        self.temperature = temperature
        self.recorder = recorder
        self.replayer = replayer
        self.lasthash = None

        self.plugin_handlers = {}
        self.plugins = []
        self.install_plugins(plugins or [])

        self.seed = seed
        self.mode = "json" if json_mode else "None"
        self.prompt = Prompt()

        self.client = client = openai.OpenAI(
            base_url=LITELLM_URL,
            api_key=LITELLM_KEY
        )

    def install_plugin(self, plugin):
        plugin.store_schema()

        self.plugins.append(plugin.get_openai_schema())
        self.plugin_handlers[plugin.name] = plugin

    def install_plugins(self, plugins):
        if isinstance(plugins, list):
            for plugin in plugins:
                self.install_plugins(plugin)
        else:
            self.install_plugin(plugins)

    @classmethod
    def setup(
        cls,
        name: str,

        # overwriting default hyperparams here
        max_tokens=None,
        temperature=None,
        seed=None,
        json_mode=False,
        plugins=None,
        recorder=None,
        replayer=None
    ):
        """Setup an LLM instance."""

        for subcls in cls.all_llm_subclasses():
            if getattr(subcls, 'name', None) == name:
                return subcls(
                    max_tokens,
                    temperature,
                    seed,
                    json_mode,
                    plugins,
                    recorder,
                    replayer
                )

        raise ValueError(f'Bad model type {name}')

    @classmethod
    def all_llm_subclasses(cls):
        """Returns all subclasses."""

        yield cls
        for subcls in cls.__subclasses__():
            for subsubcls in subcls.all_llm_subclasses():
                yield subsubcls

    @classmethod
    def all_llm_names(cls):
        """Returns the current model name and all child model names."""

        names = []
        for subcls in cls.all_llm_subclasses():
            if hasattr(subcls, 'name'):
                names.append(subcls.name)
        return names


class GPT(LLM):
    """OpenAI's GPT model encapsulator."""

    name = 'oai-gpt-3.5-turbo'
    max_tokens = 16_385

    # ref. https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
    def count_tokens(self, messages, model=None):
        """Return the number of tokens used by a list of messages."""
        if model is None:
            model = self.name

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning("OpenAI: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        if model in {
            "oai-gpt-3.5-turbo-0613",
            "oai-gpt-3.5-turbo-16k-0613",
            "oai-gpt-4-0314",
            "oai-gpt-4-32k-0314",
            "oai-gpt-4-0613",
            "oai-gpt-4-32k-0613",
            }:
            tokens_per_message = 3
            tokens_per_name = 1
        elif model == "oai-gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif "oai-gpt-3.5-turbo" in model:
            logger.warning("OpenAI: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
            return self.count_tokens(messages, model="oai-gpt-3.5-turbo-0613")
        elif "oai-gpt-4" in model:
            logger.warning("OpenAI: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
            return self.count_tokens(messages, model="oai-gpt-4-0613")
        else:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
            )
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens

    def query(self, prompt):
        """Make a single query given a prompt."""

        kwargs = {
            "model": self.name,
            "messages": prompt.get(),
            "temperature": self.temperature,
            "seed": self.seed,
        }

        if self.plugins:
            kwargs["tools"] = self.plugins

        if self.mode == "json":
            kwargs["response_format"] = {"type": "json_object"}

        # simple record and replay logic
        msg = prompt.get()[-1]
        if self.replayer:
            (self.lasthash, out) = self.replayer.get(self, self.lasthash, msg)
        else:
            out = self.client.chat.completions.create(**kwargs)

        if self.recorder:
            self.recorder.add(self, msg, out.model_dump())

        return out

    def run(self, prompt):
        """Run the query until it concludes."""

        # reset the prompt
        self.prompt = prompt

        while True:
            res = self.query(self.prompt)
            self.used_tokens = res.usage.total_tokens
            msg = res.choices[0].message

            self.prompt.append_raw(msg)

            try:
                tool_calls = msg.tool_calls
            except AttributeError:
                tool_calls = None

            if tool_calls:
                for call in tool_calls:
                    func_name = call.function.name

                    # suggest to use "eval_python()"
                    if not func_name in self.plugin_handlers:
                        self.prompt.append_tool_result(call, \
                            "ERROR: No such a function exists. Perhaps, using `execute_python()`?`")
                        continue
                    handler = self.plugin_handlers[func_name]

                    # ugly heuristic to pass the code-like non-json object to the code params
                    try:
                        args = json.loads(call.function.arguments)
                    except json.decoder.JSONDecodeError:
                        # assuming that 'execute_[lang]' accepts only code (and timeout as an optional)
                        if func_name.startswith("execute_"):
                            args = {"code": call.function.arguments}
                        else:
                            self.prompt.append_tool_result(call, \
                                "ERROR: The arguments are not well-formated (JSON decoding error)!")
                            continue

                    # pretty print the code
                    if func_name.startswith("execute_"):
                        logger.info("CALL: %s(timeout=%s)" % (func_name, args.get("timeout", "N/A")))
                        prettyprint_code(lang=func_name[8:], code=args["code"])
                    else:
                        logger.info("CALL: %s(%s)" % (func_name, call.function.arguments))

                    try:
                        ret = handler(**args)
                        ret = str(ret).rstrip()
                        self.prompt.append_tool_result(call, ret)
                        logger.info(f"> {ret}")
                        continue
                    except PluginErrorTimeout:
                        msg = "ERROR: Timeout. Increase the `timeout` param and try again."
                        self.prompt.append_tool_result(call, msg)
                        logger.info(f"> {msg}")
                        continue
                    except (PluginErrorRetry, PluginErrorGivingUp, PluginSuccess) as e:
                        logger.info(f"> Terminate the session!\n{e}")
                        raise e
                    except Exception as e:
                        self.prompt.append_tool_result(call, f"ERROR: Exception {e}.")
                        logger.warning(f"Exception: {e}.")
                        raise e

            # terminate the run
            return msg.content


class OAIGPT4(GPT):
    """OpenAI's GPT-4 model."""
    name = 'oai-gpt-4'
    max_tokens = 8_192

class OAIGPT4Turbo(GPT):
    """OpenAI's GPT-4 Turbo model."""
    name = 'oai-gpt-4-turbo'
    max_tokens = 128_000

class OAIGPT4o(GPT):
    """OpenAI's GPT-4o model."""
    name = 'oai-gpt-4o'
    max_tokens = 128_000

class GPT4(GPT):
    """OpenAI's GPT-4 model."""
    name = 'gpt-4'
    max_tokens = 8_192

class GPT4Turbo(GPT):
    """OpenAI's GPT-4 Turbo model."""
    name = 'gpt-4-turbo'
    max_tokens = 128_000

class GPT4o(GPT):
    """OpenAI's GPT-4o model."""
    name = 'gpt-4o'
    max_tokens = 128_000

class GeminiPro(GPT):
    """Google's Gemini Pro."""
    name = 'gemini-1.5-pro'
    max_tokens = 1_048_576
