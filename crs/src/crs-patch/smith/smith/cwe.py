from dataclasses import dataclass
import re

from .lib.cwe import load_cwe_summary, normalize_cwe, load_cwe_title, load_cwes # type: ignore

@dataclass
class CWE:
    _name: str
    _desc: str

    @staticmethod
    def from_str(cwe: str):
        cwe = normalize_cwe(cwe)
        m = re.match(r'CWE-(?P<id>\d+)', cwe, re.IGNORECASE)
        if m is None:
            raise ValueError(f'Invalid CWE: {cwe}')

        cwes = load_cwes()
        if cwe not in cwes:
            # Not a Top-20 CWEs
            return DummyCWE()

        cwe_id = int(m.group('id'))
        title = load_cwe_title(cwe)

        name = f"CWE-{cwe_id}: {title}"
        desc = load_cwe_summary(cwe)

        return CWE(name, desc)

    def __init__(self, name: str, desc: str):
        self._name = name
        self._desc = desc

    @property
    def name(self):
        return self._name

    @property
    def desc(self):
        return self._desc


@dataclass
class DummyCWE(CWE):
    def __init__(self): # pylint: disable=super-init-not-called
        self._name = 'CWE-???: Unknown'
        self._desc = 'Unknown'

@dataclass
class SanitizerCWE(CWE):
    def __init__(self, name): # pylint: disable=super-init-not-called
        self._name = name
        # TODO: Generate proper description to help LLMs
        self._desc = ""
