from typing import TypedDict


class LiteLlmContext(TypedDict):
    api_key: str
    base_url: str
    max_tokens: int
    model: str
