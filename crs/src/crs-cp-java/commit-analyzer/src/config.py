from typing import Literal, List, Optional, Dict
from abc import ABC, abstractmethod

from format import (
    CodeFormatter,
    AfterFunctionFormatter,
    DiffFormatter,
)
from prompt import (
    PromptCompose,
    Sequential,
    AppendCode,
    AppendHarness,
)

import logging


class Config(ABC):
    # Task config
    classification: Literal["binary", "multi-class"]
    analyze_unit: Literal["commit", "file", "function"]

    # Prompt config
    shot_num: int = 0
    strategy: List[CodeFormatter]
    prompt_compose: PromptCompose
    code_format: Literal["function", "functiondiff", "diff"]
    system_prompt_format: str
    response_format: Optional[Dict] = None
    budget = 20

    @abstractmethod
    def get_system_prompt(self, bug_type: List) -> str:
        pass

    functions: Optional[List] = None
    function_call: Optional[str] = None

    # Model config
    model: Literal["oai-gpt-4o"]

    # Misc.
    eval_config: bool = False

    def __init__(self):
        logger = logging.getLogger("Config")
        if not hasattr(self, "classification"):
            logger.error("Subclasses must define 'classification'")
            self.classification = BaseZeroShotConfig.classification
        if not hasattr(self, "analyze_unit"):
            logger.error("Subclasses must define 'analyze_unit'")
            self.analyze_unit = BaseZeroShotConfig.analyze_unit
        if not hasattr(self, "strategy"):
            logger.error("Subclasses must define 'strategy'")
            self.strategy = BaseZeroShotConfig.strategy
        if not hasattr(self, "prompt_compose"):
            logger.error("Subclasses must define 'prompt_compose'")
            self.prompt_compose = BaseZeroShotConfig.prompt_compose
        if not hasattr(self, "code_format"):
            logger.error("Subclasses must define 'code_format'")
            self.code_format = BaseZeroShotConfig.code_format
        if not hasattr(self, "system_prompt_format"):
            logger.error("Subclasses must define 'system_prompt_format'")
            self.system_prompt_format = BaseZeroShotConfig.system_prompt_format
        if not hasattr(self, "model"):
            logger.error("Subclasses must define 'model'")
            self.model = BaseZeroShotConfig.model


class BaseZeroShotConfig(Config):
    # Task cofig
    classification = "binary"
    analyze_unit = "function"

    # Prompt config
    delimiter = "xml"
    strategy: list[CodeFormatter] = [
        AfterFunctionFormatter(delimiter),
        DiffFormatter(delimiter),
    ]
    prompt_compose = AppendCode(strategy)
    code_format = "functiondiff"
    delimiter_info = " delimited by xml tags"
    system_prompt_format = """You are an automated program bug finding tool.
I am going to provide diff of a commit delimited by xml tags, and I want you to determine whether this commit introduces {bug_type} bug or not.
Deleted line is started with "-" and added line is started with "+". 
Focus on the newly added and deleted lines and their side effects on the given bug type.
Ignore the unprovided context and do not make any assumptions.
Using knowledge that already you know is allowed.

Follow the below steps to determine whether the code is vulnerable or benign:
1. Determine the type of the commit among the following: "new feature", "refactor", "performance improvement", "documentation", "test", "other".
2. Review the newly added or deleted code lines whether they are related to the given bug type. Ignore vulnerability to other bug types.
3. Determine whether the commit is vulnerable or benign based on the above steps.
Output a JSON object structured like: {{"step-1": type of the commit and its reason within 100 words, "step-2": review of the commit in perspective of the given bug type, "answer": vulnerable or benign}}, and explaination should less than 100 words.

Example problems of the same type of vulnerabilities are given below:

"""

    def get_system_prompt(self, bug_type: List) -> str:
        logger = logging.getLogger("BaseZeroShotConfig")
        if len(bug_type) != 1:
            logger.error("bug_type must be a single element list in BaseZeroShotConfig")
        return self.system_prompt_format.format(bug_type=bug_type[0])

    # Model config
    model = "oai-gpt-4o"


class CommitMultiClassConfig(Config):
    # Task cofig
    classification = "multi-class"
    analyze_unit = "commit"

    # Prompt config
    delimiter = "xml"
    strategy = [
        AfterFunctionFormatter(delimiter),
        DiffFormatter(delimiter),
    ]
    prompt_compose = Sequential([AppendCode(strategy)])
    code_format = "functiondiff"
    system_prompt_format = """You are an automated program bug finding tool.
I am going to provide funciton and diff of a commit delimited by xml tags, and I want you to determine whether changed lines of the commit introduce one of {bug_type} or not.
Between diff tags, deleted lines are started with "-" and added lines are started with "+".
Focus on the newly changed lines and their side effects to the original system.
Do not make any assumptions on unseen codebase and ignore vulnerability that need to assume mistakes in unseen context.

Follow the below steps to determine whether the code is vulnerable or benign:
Step 1. Determine the type of the commit among the following: "new feature", "refactor", "performance improvement", "documentation", "test", "other".
Step 2. Determine candidate bug types related to the changed lines. Ignore other bug types that cannot be related to the changed lines.
Step 3. Explain why the changed lines can trigger each candidate bug types. Use at most 1000 words for each bug type.
Step 4. Verify the each answer and prioritize the most likely bug type. If the changed lines are not related to any bug types, consider it as benign.
Step 5. Give an answer vulnerable to which "bug type" or "benign" based on the above steps.
Response the above steps and output an answer.
"""
    # Output should be JSON object structured like {{"step-1": ...,
    # "step-2": ...,
    # "step-3": ...,
    # "step-4": ...,
    # "answer": one of {bug_type} or "benign"}}.

    def get_system_prompt(self, bug_type: List) -> str:
        return self.system_prompt_format.format(bug_type=str(bug_type))

    # Model config
    model = "oai-gpt-4o"


class DevZeroShotConfig(Config):
    # Task cofig
    classification = "binary"
    analyze_unit = "commit"

    # Prompt config
    delimiter = "xml"
    strategy = [
        AfterFunctionFormatter(delimiter),
        DiffFormatter(delimiter),
    ]
    prompt_compose = Sequential(
        [
            AppendCode(strategy),
            # AppendHarness(tag="test_harness"),
        ]
    )
    code_format: str = "functiondiff"

    # delimiter_info: str = ""
    system_prompt_format: str = """You are an automated program bug finding tool.
I am going to provide funciton and diff of a commit delimited by xml tags, and I want you to determine whether this commit introduces {bug_type} or not.
Deleted line is started with "-" and added line is started with "+". 
Focus on the newly added and deleted lines and their side effects to the original system at the given bug types' aspect.
Do not make any assumptions and ignore vulnerability that assumes mistakes in unseen context.
Using security-related knowledge that already you know is allowed.

Follow the below steps to determine whether the code is vulnerable or benign:
Step 1. Determine the type of the commit among the following: "new feature", "refactor", "performance improvement", "documentation", "test", "other".
Step 2. Determine the changed code lines are related to the given bug type. Ignore vulnerability to other bug types.
Step 3. Determine whether the commit is vulnerable or benign based on the above steps.
Step 4. The last json object key must be the "answer". Although the changed code itself is vulnerable, if the changed code cannot be accessed by the test harness, answer "benign".

Response the above steps and output an answer.

---------
schema:
{{
    "type": "object",
    "properties": {{
        "answer": {{
            "type": "string",
            "description": "determine whether the code is vulnerable or benign",
        }},
        "explanation": {{
            "type": "string",
            "description": "Describe the steps you took",
        }},
    }},
    "required": ["answer", "explanation"],
}}
--------
JSON:
{{
    "answer": {{"
"""

    # Model config
    model = "oai-gpt-4o"


class BinaryCommitHarness(Config):
    # Task cofig
    classification = "binary"
    analyze_unit = "commit"

    # Prompt config
    delimiter = "xml"
    strategy = [
        AfterFunctionFormatter(delimiter),
        DiffFormatter(delimiter),
    ]
    prompt_compose = Sequential(
        [
            AppendCode(strategy),
            AppendHarness(tag="test_harness", harness_path="tbd"),
        ]
    )
    code_format = "functiondiff"
    system_prompt_format = """You are an automated program bug finding tool.
I am going to provide funciton and diff of a commit delimited by xml tags, and I want you to determine whether this commit introduces {} bug or not.
I am interested in vulnerabilities that can be triggered by the given harness.
Deleted line is started with "-" and added line is started with "+". 
Focus on the newly added and deleted lines and their side effects to the original system at the given bug types' aspect.
Do not make any assumptions and ignore vulnerability that assumes mistakes in unseen context.
Using security-related knowledge that already you know is allowed.

Follow the below steps to determine whether the code is vulnerable or benign:
Step 1. Determine the type of the commit among the following: "new feature", "refactor", "performance improvement", "documentation", "test", "other".
Step 2. Determine the changed code lines can be accessed by the given harness. If the changed code is not related to the given harness, ignore the remaining steps and just answer "benign".
Step 3. Determine the changed code lines are related to the given bug type. Ignore vulnerability to other bug types.
Step 4. Determine whether the commit is vulnerable or benign based on the above steps.
Step 5. Although the changed code itself is vulnerable, if the changed code cannot be accessed by the test harness, answer "benign".
If the answer is vulnerable, give a blob that can trigger the vulnerability through the test harness.
Response the above steps and output an answer.
Output should be: "step-1": ..., 
"step-2": ..., 
"step-3": ..., 
"step-4": ...,
"blob": ..., 
"answer": ....

Last, I want to use the extract_answer function_call to print the answer and blob from the given response.
Therefore, you MUST give parameters to the function_call to me.
"""

    functions = [
        {
            "name": "extract_answers",
            "type": "function",
            "description": "This print the answer and blob from the given response.",
            "step-4": ...,
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": 'determine whether the code is vulnerable or benign. answer must be "vulnerable" or "benign".',
                    },
                    "blob": {
                        "type": "string",
                        "description": 'blob to trigger the vulnerability via the given harness. if the code is benign, this should be empty "".',
                    },
                },
                "required": ["answer", "blob"],
            },
        }
    ]
    function_call = {"name": "extract_answers", "type": "auto"}

    # Model config
    model = "oai-gpt-4o"


class ConfigFactory:
    _config_classes = {}

    @staticmethod
    def _load_config_classes():
        from sys import modules
        import inspect

        current_module = modules[__name__]
        for name, obj in inspect.getmembers(current_module, inspect.isclass):
            if issubclass(obj, Config) and obj is not Config:
                ConfigFactory._config_classes[name.lower()] = obj

    @staticmethod
    def createConfig(type: str):
        if not ConfigFactory._config_classes:
            ConfigFactory._load_config_classes()

        config_class = ConfigFactory._config_classes.get(type.lower())
        if config_class:
            return config_class()
        else:
            return Config
