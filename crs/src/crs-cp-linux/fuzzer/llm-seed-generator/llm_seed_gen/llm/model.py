from abc import ABC, abstractmethod


class Model(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        pass

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        pass

    @property
    @abstractmethod
    def context_window(self) -> int:
        pass


class OaiGpt4o(Model):
    @property
    def name(self) -> str:
        return 'oai-gpt-4o'

    @property
    def provider(self) -> str:
        return 'openai'

    @property
    def context_window(self) -> int:
        return 128000

    @property
    def max_tokens(self) -> int:
        return 4096
