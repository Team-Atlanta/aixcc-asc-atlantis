import logging

import backoff
from httpx import ConnectError
from openai import APIConnectionError, InternalServerError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from redia.conversation.contexts import ConversationContext
from redia.utils.context import RequiresContext


@backoff.on_exception(
    backoff.expo,
    (
        APIConnectionError,
        InternalServerError,
        RateLimitError,
        ConnectError,
    ),
    max_tries=10,
    on_backoff=lambda details: logging.error(
        f"{details.get('exception','Exception')}\n"
        + f"Retry in {details['wait']:.1f} seconds."
        if "wait" in details
        else ""
    ),
)
def completion_with_retries(
    messages: list[ChatCompletionMessageParam],
    temperature: float | None = None,
) -> RequiresContext[ChatCompletion, ConversationContext]:
    def _(context: ConversationContext):
        client = OpenAI(
            api_key=context["api_key"],
            base_url=context["base_url"],
        )

        response = client.chat.completions.create(
            model=context["model"],
            messages=messages,
            temperature=temperature,
        )

        return response

    return RequiresContext(_)
