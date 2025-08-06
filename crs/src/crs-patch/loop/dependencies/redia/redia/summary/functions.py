from openai.types.chat import ChatCompletionMessageParam

from redia.conversation.functions import completion_with_retries
from redia.summary.contexts import SummaryContext
from redia.token.functions import (
    number_of_tokens_in_conversation,
    number_of_tokens_in_message,
)
from redia.utils.context import RequiresContext

_SUMMARIZE_PROMPT = """
*Briefly* summarize this partial conversation about programming.
Include less detail about older parts and more detail about the most recent messages.
Start a new paragraph every time the topic changes!

This is only part of a longer conversation so *DO NOT* conclude the summary with language like "Finally, ...". Because the conversation continues after the summary.
The summary *MUST* include the function names, libraries, packages that are being discussed.
The summary *MUST* include the filenames that are being referenced by the assistant inside the ```...``` fenced code blocks!
The summaries *MUST NOT* include ```...``` fenced code blocks!

Phrase the summary with the USER in first person, telling the ASSISTANT about the conversation.
Write *as* the user.
The user should refer to the assistant as *you*.
Start the summary with "I asked you...".
""".strip()

_SUMMARY_PREFIX = "I spoke to you previously about a number of things.\n"


def conversation_as_summarized_conversation(
    messages: list[ChatCompletionMessageParam], max_tokens: int = 1024, depth: int = 0
) -> RequiresContext[list[ChatCompletionMessageParam], SummaryContext]:
    def _(context: SummaryContext):

        if (
            number_of_tokens_in_conversation(messages)(context) <= max_tokens
            and depth == 0
        ):
            return messages

        head, tail = split_conversation_by_tail_max_tokens(
            messages, tail_max_tokens=max_tokens // 2
        )(context)

        summary = [conversation_as_summarized_message(head)(context)] + tail

        if number_of_tokens_in_conversation(summary)(context) <= max_tokens:
            return summary
        else:
            return conversation_as_summarized_conversation(
                summary, max_tokens, depth + 1
            )(context)

    return RequiresContext(_)


def split_conversation_by_tail_max_tokens(
    messages: list[ChatCompletionMessageParam],
    tail_max_tokens: int,
) -> RequiresContext[
    tuple[list[ChatCompletionMessageParam], list[ChatCompletionMessageParam]],
    SummaryContext,
]:

    def _(
        context: SummaryContext,
        head: list[ChatCompletionMessageParam],
        tail: list[ChatCompletionMessageParam],
        tail_max_tokens: int,
    ) -> tuple[list[ChatCompletionMessageParam], list[ChatCompletionMessageParam]]:
        match sum(number_of_tokens_in_message(message)(context) for message in tail):
            case tail_tokens if tail_tokens <= tail_max_tokens:
                if len(head) > 0 and head[-1]["role"] != "assistant":
                    return head, tail
                else:
                    return head[:-1], [head[-1]] + tail
            case __:
                return _(
                    context,
                    head + [tail[0]],
                    tail[1:],
                    tail_max_tokens,
                )

    return RequiresContext(lambda context: _(context, [], messages, tail_max_tokens))


def conversation_as_summarized_message(
    messages: list[ChatCompletionMessageParam],
) -> RequiresContext[ChatCompletionMessageParam, SummaryContext]:
    formatted_messages = [
        _formatted_message(message)
        for message in messages
        if message["role"].upper() in ["USER", "ASSISTANT"]
    ]

    def _(context: SummaryContext) -> ChatCompletionMessageParam:
        response = completion_with_retries(
            messages=[
                {
                    "role": "system",
                    "content": _SUMMARIZE_PROMPT,
                },
                {
                    "role": "user",
                    "content": "\n".join(formatted_messages),
                },
            ],
            temperature=0.0,
        )(context)

        return {
            "role": "user",
            "content": _SUMMARY_PREFIX + str(response.choices[0].message.content),
        }

    return RequiresContext(_)


def _formatted_message(message: ChatCompletionMessageParam):
    return f"# {message['role']}\n{message['content'] if 'content' in message else ''}".strip()
