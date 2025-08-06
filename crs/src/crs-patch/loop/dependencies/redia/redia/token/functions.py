import tiktoken
import tree_sitter
from openai.types.chat import ChatCompletionMessageParam
from tree_sitter_languages import get_language, get_parser

from redia.token.contexts import TokenContext
from redia.utils.context import RequiresContext


def split_text_by_tree_sitter_blocks(
    text: str, language: str, max_tokens: int, encoding: tiktoken.Encoding
) -> list[str]:

    if len(encoding.encode(text)) <= max_tokens:
        return [text]

    def setup_parser():
        parser = get_parser(language)
        parser.set_language(get_language(language))
        return parser

    def traverse_tree(node: tree_sitter.Node, depth: int = 0) -> list[tuple[int, int]]:
        if depth > 1 or node.type == "ERROR":
            return []

        if depth == 1 or node.child_count == 0:
            return [(node.start_byte, node.end_byte)]

        ranges: list[tuple[int, int]] = []
        for child in node.children:
            ranges.extend(traverse_tree(child, depth + 1))
        return ranges

    def create_largest_chunks(ranges: list[tuple[int, int]]) -> list[str]:
        chunks: list[str] = []
        current_chunk = ""
        current_tokens = 0

        for (start, _), (next_start, _) in zip(
            ranges, ranges[1:] + [(len(text), len(text))]
        ):
            block = text[start:next_start]
            block_tokens = len(encoding.encode(block))

            if current_tokens + block_tokens > max_tokens:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = block
                current_tokens = block_tokens
            else:
                current_chunk += block
                current_tokens += block_tokens

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    parser = setup_parser()
    tree = parser.parse(bytes(text, "utf8"))
    ranges = traverse_tree(tree.root_node)
    return create_largest_chunks(ranges)


def number_of_tokens_in_conversation(
    messages: list[ChatCompletionMessageParam],
) -> RequiresContext[int, TokenContext]:
    return RequiresContext(
        lambda context: sum(
            number_of_tokens_in_message(message)(context) for message in messages
        )
    )


def number_of_tokens_in_message(
    message: ChatCompletionMessageParam,
) -> RequiresContext[int, TokenContext]:

    def _(context: TokenContext):
        if "content" not in message:
            return 0

        match message["content"]:
            case str():
                encoding = tiktoken.encoding_for_model(
                    context["model"].replace("oai-", "", 1).replace("gpt-4o", "gpt-4")
                )
                num_tokens = len(encoding.encode(message["content"]))
            case _:
                assert False, f"Unexpected message content: {message['content']}"

        return num_tokens

    return RequiresContext(_)
