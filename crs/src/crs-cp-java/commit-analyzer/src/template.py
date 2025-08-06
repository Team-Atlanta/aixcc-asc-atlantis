from typing import List
from format import (
    CodeFormatter,
    DiffFormatter,
    BeforeFunctionFormatter,
    AfterFunctionFormatter,
    FormatterCompose,
)


class BenignTemplate:
    benign_strategy: List[CodeFormatter] = [
        BeforeFunctionFormatter,
        DiffFormatter,
    ]

    def __init__(self, benign_strategy=None):
        if benign_strategy is not None:
            self.benign_strategy = benign_strategy

    def apply(self):
        {
            "question": FormatterCompose(self.benign_strategy).apply(input),
            "answer": "benign",
        }


class VulnerableBenignTemplate:
    vulnerable_strategy: List[CodeFormatter] = [
        AfterFunctionFormatter,
        DiffFormatter,
    ]

    def __init__(
        self, classification, vulnerable_strategy=None, benign_strategy=None
    ) -> None:
        self.classfication = classification
        if vulnerable_strategy is not None:
            self.vulnerable_strategy = vulnerable_strategy

    def apply(self, input):
        if self.classfication == "binary":
            answer = "vunlerable"
        else:
            answer = input.bug_type

        return {
            "question": FormatterCompose(self.vulnerable_strategy).apply(input),
            "answer": answer,
        }
