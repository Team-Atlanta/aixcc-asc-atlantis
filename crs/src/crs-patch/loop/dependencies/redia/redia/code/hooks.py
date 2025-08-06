from pathlib import Path

from openai.types.chat import ChatCompletionMessageParam

from redia.code.contexts import CodingContext
from redia.code.functions import suggest as _suggest
from redia.code.models import CodingRecipe
from redia.code.recipes import conflict_marker_recipe
from redia.utils.context import RequiresContext


def use_coder(recipe: CodingRecipe = conflict_marker_recipe):
    mutable_history: list[ChatCompletionMessageParam] = []

    def suggest(
        user_message: str, absolute_paths_of_target_files: list[Path]
    ) -> RequiresContext[str, CodingContext]:
        nonlocal mutable_history

        def _(context: CodingContext) -> str:
            nonlocal mutable_history

            try:
                response = _suggest(
                    recipe=recipe,
                    message=user_message,
                    history=mutable_history,
                    absolute_paths_of_target_files=absolute_paths_of_target_files,
                )(context)

                conversation: list[ChatCompletionMessageParam] = [
                    {
                        "role": "user",
                        "content": user_message,
                    },
                    {
                        "role": "assistant",
                        "content": response,
                    },
                ]

                mutable_history += conversation

                return response
            except Exception as error:
                conversation: list[ChatCompletionMessageParam] = [
                    {
                        "role": "user",
                        "content": user_message,
                    },
                    {
                        "role": "assistant",
                        "content": f"Error: {error}",
                    },
                ]

                mutable_history += conversation

                raise error

        return RequiresContext(_)

    def drop_last_conversion_silently():
        nonlocal mutable_history

        if (
            len(mutable_history) >= 2
            and mutable_history[-1]["role"] == "assistant"
            and mutable_history[-2]["role"] == "user"
        ):
            mutable_history = mutable_history[:-2]
        else:
            mutable_history = mutable_history

        return None

    return suggest, drop_last_conversion_silently
