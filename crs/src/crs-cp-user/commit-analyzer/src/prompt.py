from typing import Dict, List
from dataclasses import dataclass
from format import FormatterCompose
from dataset import FunctionChange, CommitChange
from abc import ABC, abstractmethod


class PromptCompose(ABC):
    @abstractmethod
    def __call__(self, input: FunctionChange | CommitChange, prev_prompt: str) -> str:
        pass


class Sequential(PromptCompose):
    def __init__(self, prompts: List[PromptCompose]):
        self.prompts = prompts

    def __call__(self, input: FunctionChange | CommitChange, prev_prompt: str) -> str:
        for prompt in self.prompts:
            prev_prompt = prompt(input, prev_prompt)
        return prev_prompt


class AppendCode(PromptCompose):
    def __init__(self, strategy: List):
        self.strategy = strategy

    def __call__(self, input: FunctionChange | CommitChange, prev_prompt: str) -> str:
        formatter = FormatterCompose(self.strategy)
        formatted_code = formatter.apply(input)

        if input == "":
            return formatted_code
        else:
            return f"{prev_prompt}\n\n{formatted_code}"


class AppendHarness(PromptCompose):
    def __init__(self, harness_path, tag: str):
        # in Dev. TODO should be determined dynamically
        self.harness_path = harness_path
        self.tag = tag

    def __call__(self, input: FunctionChange | CommitChange, prev_prompt: str) -> str:
        if prev_prompt == "":
            results = "{prev_prompt}{data}"
        else:
            if self.tag != "":
                results = "{prev_prompt}\n\n<{tag}>\n{data}\n</{tag}>"
            else:
                results = "{prev_prompt}\n\n{data}"

        with open(self.harness_path, "r") as f:
            data = f.read()
        return results.format(prev_prompt=prev_prompt, data=data.strip(), tag=self.tag)


@dataclass
class Prompt:
    system_prompt: str
    examples: Dict[str, str]
    query: str


class PromptBuilder:
    def __init__(self):
        self.system_prompt = ""
        self.examples = {}
        self.query = ""

    def add_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        return self

    def add_query(self, input, config):
        promptCompose = config.prompt_compose
        self.query = promptCompose(input, "")
        return self

    def build(self) -> Prompt:
        return Prompt(self.system_prompt, self.examples, self.query)
