import os
from pathlib import Path

import tiktoken
from openai.types.chat import ChatCompletionMessageParam
from pygments.lexers import guess_lexer_for_filename

from redia.code.contexts import CodingContext
from redia.code.exceptions import WrongFormatInResponseError
from redia.code.models import CodingRecipe
from redia.conversation.functions import completion_with_retries
from redia.repository_map.functions import repository_map_as_prompt, sorted_tags_by_rank
from redia.summary.functions import conversation_as_summarized_conversation
from redia.token.functions import (
    number_of_tokens_in_conversation,
    split_text_by_tree_sitter_blocks,
)
from redia.utils.context import RequiresContext

# FIXME: Hardcoded value.
os.environ["TIKTOKEN_CACHE_DIR"] = str(
    Path(__file__).parent.parent.parent / "artifacts" / "tiktoken_cache"
)


def suggest(
    recipe: CodingRecipe,
    message: str,
    history: list[ChatCompletionMessageParam],
    absolute_paths_of_target_files: list[Path],
) -> RequiresContext[str, CodingContext]:

    def _(context: CodingContext):
        summarized: list[ChatCompletionMessageParam] = [
            *conversation_as_summarized_conversation(history)(context),
            {"role": "assistant", "content": "Ok."},
        ]

        conversations = _format_conversations_of_files(
            raw_message=message,
            summarized_conversation=summarized,
            target_files=list(set(absolute_paths_of_target_files)),
            system_main_prompt=recipe.system_main_prompt,
            system_reminder_prompt=recipe.system_reminder_prompt,
            file_content_prefix=recipe.file_content_prefix,
        )(context)

        content: str = ""
        for conversation in conversations:
            context["logger"].debug("[Start of the Conversation]")
            context["logger"].debug(f"user:\n{message.strip()}")

            response = completion_with_retries(conversation)(context)

            suggestion_message = response.choices[0].message

            assert suggestion_message.content is not None

            context["logger"].debug(
                f"{suggestion_message.role}:\n{suggestion_message.content.strip()}"
            )

            context["logger"].debug("[End of the Conversation]")

            content += suggestion_message.content

        try:
            diff = recipe.response_as_git_diff(content, context["source_directory"])
        except AssertionError as e:
            raise WrongFormatInResponseError(f"Failed to parse response: {e}") from e

        return diff

    return RequiresContext(_)


def _format_conversations_of_files(
    raw_message: str,
    summarized_conversation: list[ChatCompletionMessageParam],
    target_files: list[Path],
    system_main_prompt: str,
    system_reminder_prompt: str,
    file_content_prefix: str,
) -> RequiresContext[list[list[ChatCompletionMessageParam]], CodingContext]:
    return RequiresContext(
        lambda context: [
            _format_conversations_of_file(
                raw_message=raw_message,
                summarized_conversation=summarized_conversation,
                target_file=target_file,
                target_files=target_files,
                system_main_prompt=system_main_prompt,
                system_reminder_prompt=system_reminder_prompt,
                file_content_prefix=file_content_prefix,
            )(context)
            for target_file in target_files
        ]
    )


def _format_conversations_of_file(
    raw_message: str,
    summarized_conversation: list[ChatCompletionMessageParam],
    target_file: Path,
    target_files: list[Path],
    system_main_prompt: str,
    system_reminder_prompt: str,
    file_content_prefix: str,
) -> RequiresContext[list[ChatCompletionMessageParam], CodingContext]:
    def _(context: CodingContext):
        user_messages: list[ChatCompletionMessageParam] = [
            {"role": "user", "content": raw_message},
        ]

        target_code = target_file.read_text()

        lexer = guess_lexer_for_filename(str(target_file), target_code)

        assert lexer is not None, f"Failed to guess lexer for {target_file}"

        target_chunks = split_text_by_tree_sitter_blocks(
            target_code,
            language=lexer.name.lower(),
            max_tokens=_max_input_tokens_of_model(context["model"])
            - 128,  # FIXME: Hardcoded value.
            encoding=tiktoken.get_encoding("cl100k_base"),
        )

        file_message_pairs: list[
            tuple[ChatCompletionMessageParam, ChatCompletionMessageParam]
        ] = [
            (
                {
                    "role": "user",
                    "content": f"{file_content_prefix}\nfile: {target_file.relative_to(context['source_directory'])}\n```\n{target_chunk}\n```\n",
                },
                {
                    "role": "assistant",
                    "content": "Ok.",
                },
            )
            for target_chunk in target_chunks
        ]

        file_messages = [
            message for message_pair in file_message_pairs for message in message_pair
        ]

        prelude_messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": f"{system_main_prompt}\n{system_reminder_prompt}",
            },
            *summarized_conversation,
            {
                "role": "user",
                "content": repository_map_as_prompt(
                    sorted_tags_by_rank(
                        target_files, others=[]
                    ),  # FIXME: Currently not loading whole files.
                    context["source_directory"],
                    token_counts=_max_input_tokens_of_model(context["model"]),
                    number_of_tokens=_number_of_tokens(context["model"]),
                ),
            },
            {"role": "assistant", "content": "Ok."},
            *file_messages,
        ]

        reminder_messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": system_reminder_prompt,
            }
        ]

        partial_messages = prelude_messages + user_messages
        total_messages = prelude_messages + user_messages + reminder_messages

        if number_of_tokens_in_conversation(total_messages)(
            context
        ) <= _max_input_tokens_of_model(context["model"]):
            return total_messages
        else:
            return partial_messages

    return RequiresContext(_)


def _max_input_tokens_of_model(model: str) -> int:
    match model:
        case model if model.endswith("gpt-4"):
            return 8192
        case model if model.endswith("gpt-4o"):
            return 128000
        case model if model.endswith("gpt-4-turbo"):
            return 128000
        case model if model.endswith("gpt-3.5-turbo"):
            return 4097
        case _:
            assert False, f"Unsupported model: {model}"


def _number_of_tokens(model: str):
    def _(s: str):
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(s))

        return num_tokens

    return _
