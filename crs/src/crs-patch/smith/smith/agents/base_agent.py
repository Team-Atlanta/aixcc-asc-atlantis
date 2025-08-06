from abc import ABC, abstractmethod
from typing import Dict

from smith.bug import Bug
from smith.model import Dialog, Model

class Agent(ABC):
    @abstractmethod
    def __init__(self, model: Model, bug: Bug, temperature: float):
        pass

    @abstractmethod
    def query(self, message: str):
        pass

    @abstractmethod
    def get_patch_diff(self) -> str:
        pass

    @abstractmethod
    def get_dialogs(self) -> Dialog:
        pass

    @abstractmethod
    def model_converter(self) -> Dict[str,str]:
        pass

    @staticmethod
    @abstractmethod
    def name() -> str:
        pass
