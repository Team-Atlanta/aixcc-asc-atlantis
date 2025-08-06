import difflib
from pathlib import Path
from typing import TypeAlias

import pygit2
from openai import OpenAI

from loop.commons.context.models import RequiresContext
from loop.framework.action.models import Action
from loop.framework.action.variants import DiffAction, RuntimeErrorAction
from loop.framework.agent.protocols import AgentProtocol
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.functions import edits_from_detection
from loop.framework.detection.models import Detection
from loop.framework.lite_llm.contexts import LiteLlmContext
from loop.framework.seed.models import Seed
from loop.framework.seed.variants import ErrorSeed, InitialSeed, PlainSeed, PrefixSeed
from loop.framework.wire.context import WireContext

_Edit: TypeAlias = tuple[tuple[str, Path], tuple[str, Path]]


class InfillingAgent(AgentProtocol):
    def __init__(self, lite_llm_context: LiteLlmContext) -> None:
        self.lite_llm_context = lite_llm_context

    def act(
        self, detection: Detection, challenge_source: ChallengeSource, seed: Seed
    ) -> RequiresContext[Action, WireContext]:
        def _(context: WireContext) -> Action:
            try:
                edits = list(edits_from_detection(detection, challenge_source))

                diff = "\n\n".join(
                    [
                        _diff_from_edit(
                            edit,
                            seed,
                            detection,
                            challenge_source,
                            self.lite_llm_context,
                        )
                        for edit in edits
                    ]
                )

                context["logger"].info(f"Suggested diff:\n{diff}")

                return DiffAction(diff)

            except Exception as e:
                context["logger"].exception(e)
                return RuntimeErrorAction(e)

        return RequiresContext(_)


def _diff_from_edit(
    edit: _Edit,
    seed: Seed,
    detection: Detection,
    challenge_source: ChallengeSource,
    lite_llm_context: LiteLlmContext,
):
    match seed:
        case InitialSeed():
            prompt_prefix = ""
        case PrefixSeed(content):
            prompt_prefix = f"Considering this prefix:\b{content}\n"
        case ErrorSeed(message):
            prompt_prefix = message
        case PlainSeed(content):
            prompt_prefix = content

    client = OpenAI(
        api_key=lite_llm_context["api_key"], base_url=lite_llm_context["base_url"]
    )

    (before_block, before_path), (after_block, after_path) = edit

    repository = pygit2.Repository(str(challenge_source.source_directory))

    commit = repository.get(detection.bug_introduce_commit).peel(1).parents[0]

    tree = commit.tree

    blob = tree[str(before_path)].peel(3)

    original_code = blob.data.decode("utf-8")

    masked_code = original_code.replace(before_block, "\n[INFILL]\n")

    block_diff_without_line_number = "".join(
        list(
            difflib.unified_diff(
                before_block.splitlines(keepends=True),
                after_block.splitlines(keepends=True),
                lineterm="",
            )
        )[3:]
    )

    response = client.chat.completions.create(
        model=lite_llm_context["model"],
        messages=[
            {
                "role": "system",
                "content": """Act as an expert software whitehat hacker.
You are diligent and thorough in your responses.
You always implement code rather than just describing it.
Your response will replace the [INFILL] token in the code. Provide only the code for that section without using backticks.
Use best practices and follow established coding conventions.
Utilize existing libraries and conventions present in the code base.
Implement the requested changes or additions without asking for clarification.
You should not modify code outside the [INFILL] section.

# Example conversation 1:

## USER: 
from flask import Flask

app = Flask(__name__)

@app.route('/div/<int:n>/<int:d>')
def divide(n, d):
    if d == 0:
        return 'Error: Division by zero'
    else:
        result = n / d
        return str(result)

def factorial(n):
[INFILL]

@app.route('/factorial/<int:n>')
def get_factorial(n):
    return str(factorial(n))

if __name__ == '__main__':
    print("Starting...")
    app.run()

## ASSISTANT: Ok.

## USER: Implement the factorial function.

## ASSISTANT:
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)
""",
            },
            {"role": "user", "content": masked_code},
            {"role": "assistant", "content": "Ok."},
            {
                "role": "user",
                "content": prompt_prefix
                + "Fix the code considering the following vulnerable diff:\n"
                + block_diff_without_line_number,
            },
        ],
    )

    infill = response.choices[0].message.content

    infilled_code = masked_code.replace("[INFILL]", infill or "")

    latest_commit = repository.get(repository.head.target).peel(1)

    latest_tree = latest_commit.tree

    latest_blob = latest_tree[str(before_path)].peel(3)

    latest_code = latest_blob.data.decode("utf-8")

    diff = "".join(
        list(
            difflib.unified_diff(
                latest_code.splitlines(keepends=True),
                infilled_code.splitlines(keepends=True),
                lineterm="\n",
                fromfile=str(before_path),
                tofile=str(after_path),
            )
        )
    )

    return diff
