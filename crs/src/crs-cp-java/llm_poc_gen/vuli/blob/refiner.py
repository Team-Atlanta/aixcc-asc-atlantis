from abc import ABC, abstractmethod
from functools import reduce
import re


class Refine(ABC):
    @abstractmethod
    def refine(self, data: str) -> list[str]:
        pass


class Refine1(Refine):
    def refine(self, data: str) -> list[str]:
        return data[1:-1] if data.startswith('"') and data.endswith('"') else ""


class Refine2(Refine):
    def refine(self, data: str) -> list[str]:
        regex = r"\"(.*?)\"\s*\.getBytes\(\)"
        matched = re.search(regex, data)
        return matched.group(1) if matched else ""


class Refine3(Refine):
    def refine(self, data: str) -> list[str]:
        # This pattern handles such as [byte, byte, byte, ... ].
        if not data.startswith("[") or not data.endswith("]"):
            return ""

        data = data[1:-1]
        tokens = list(map(lambda x: x.strip(), data.split(",")))
        for i in range(0, len(tokens)):
            token = tokens[i]
            try:
                token = int(token)
                tokens[i] = (
                    chr(token) if 32 <= int(token) <= 126 else "\\" + oct(token)[2:]
                )
            except ValueError:
                pass
        return "".join(tokens)


class Refine4(Refine):
    def refine(self, data: str) -> list[str]:
        # This pattern handles such as `byte[] variable = "something...`"
        regex = r'byte\[\] \S+ = "(.*?)";'
        matched = re.search(regex, data)
        return matched.group(1) if matched else ""


class Refine5(Refine):
    def refine(self, data: str) -> list[str]:
        # This pattern handles such as `String variable = "something...`"
        regex = r'String \S+ = "(.*?)";'
        matched = re.search(regex, data)
        return matched.group(1) if matched else ""


class Refine6(Refine):
    def refine(self, data: str) -> list[str]:
        # This pattern handles such as 'perl -e ...`
        if data.startswith("perl -e 'print \"") and data.count('"') == 2:
            return data[data.find('"') + 1 : data.rfind('"')]
        return ""


class Refiner:
    refiners = []

    def __init__(self):
        self.refiners = [Refine1(), Refine2(), Refine3(), Refine4(), Refine5(), Refine6()]

    def refine(self, data: str) -> set[str]:
        refined = set(map(lambda x: x.refine(data), self.refiners))
        refined = set(filter(lambda x: len(x) > 0, refined))
        if len(refined) == 0:
            refined.add(data)
        return refined
