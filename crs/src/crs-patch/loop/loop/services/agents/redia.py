from pathlib import Path

from redia.code.contexts import CodingContext
from redia.code.exceptions import WrongFormatInResponseError
from redia.code.hooks import use_coder
from redia.code.recipes import next_conflict_marker_recipe

from loop.commons.context.models import RequiresContext
from loop.framework.action.models import Action
from loop.framework.action.variants import (
    DiffAction,
    RuntimeErrorAction,
    WrongFormatAction,
)
from loop.framework.agent.protocols import AgentProtocol
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.functions import edits_from_detection
from loop.framework.detection.models import Detection
from loop.framework.lite_llm.contexts import LiteLlmContext
from loop.framework.seed.models import Seed
from loop.framework.seed.variants import ErrorSeed, InitialSeed, PlainSeed, PrefixSeed
from loop.framework.wire.context import WireContext


class RediaAgent(AgentProtocol):
    def __init__(self, lite_llm_context: LiteLlmContext) -> None:
        self.lite_llm_context = lite_llm_context
        (self._suggest, self._drop_last_conversation) = use_coder(
            next_conflict_marker_recipe
        )

    def act(
        self, detection: Detection, challenge_source: ChallengeSource, seed: Seed
    ) -> RequiresContext[Action, WireContext]:
        def _(context: WireContext) -> Action:
            edits = list(edits_from_detection(detection, challenge_source))

            prompts_from_potentially_buggy_blocks = list(
                _edits_to_prompts(edits, challenge_source)
            )

            if len(prompts_from_potentially_buggy_blocks) == 0:
                return RuntimeErrorAction(
                    ValueError("No edits found in the detection object")
                )

            match seed:
                case InitialSeed():
                    prompt_prefix = ""
                case PrefixSeed(content):
                    prompt_prefix = f"Considering this prefix:\b{content}\n"
                case ErrorSeed(message):
                    prompt_prefix = message
                case PlainSeed(content):
                    prompt_prefix = content

            try:
                coding_context: CodingContext = {
                    "api_key": self.lite_llm_context["api_key"],
                    "base_url": self.lite_llm_context["base_url"],
                    "model": self.lite_llm_context["model"],
                    "logger": context["logger"],
                    "source_directory": challenge_source.source_directory,
                    "working_directory": challenge_source.challenge_project_directory,
                }

                diff = self._suggest(
                    (
                        prompt_prefix
                        + f"\nDon't forget to add <<<<<<< SEARCH part! Fix {challenge_source.sanitizer_name} vulnerabilities in these lines.:\n"
                        + "\n\n".join(prompts_from_potentially_buggy_blocks)
                        + "\n"
                    ),
                    absolute_paths_of_target_files=[
                        challenge_source.source_directory / path
                        for (_, _), (_, path) in edits
                    ],
                )(coding_context)

                context["logger"].info(f"Suggested diff:\n{diff}")
            except WrongFormatInResponseError as e:
                return WrongFormatAction(e)
            except Exception as e:
                return RuntimeErrorAction(e)

            return DiffAction(content=diff)

        return RequiresContext(_)

    def on_sound_effect(self) -> None: ...

    def on_not_sound_effect(self) -> None:
        self._drop_last_conversation()


def _edits_to_prompts(
    edits: list[tuple[tuple[str, Path], tuple[str, Path]]],
    challenge_source: ChallengeSource,
):
    for edit in edits:
        (_, _), (_, new_file_path) = edit
        if (challenge_source.source_directory / new_file_path).exists():
            yield _edit_to_prompt(edit)
        else:
            continue


def _edit_to_prompt(edit: tuple[tuple[str, Path], tuple[str, Path]]):
    (_, _), (after, new_file_path) = edit

    return f"file: {new_file_path}\n```\n{after}\n```"
