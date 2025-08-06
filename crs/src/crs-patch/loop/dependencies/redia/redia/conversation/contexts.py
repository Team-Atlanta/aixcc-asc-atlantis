from typing import TypedDict


class ConversationContext(TypedDict):
    model: str
    api_key: str
    base_url: str
