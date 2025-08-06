import os
import re
from dataclasses import dataclass

# From skynet
def normalize_cwe(cwe):
    if isinstance(cwe, str):
        cwe = cwe.strip().lower()
        if cwe.isnumeric():
            cwe = int(cwe)
        elif cwe.startswith("cwe"):
            cwe = cwe[3:]
            cwe = cwe.replace(":", "")
            cwe = cwe.replace("-", "")
            cwe = int(cwe.strip())
    assert isinstance(cwe, int)
    return f"CWE-{cwe:03d}"

def load_cwe_summary(cwe):
    assert cwe.startswith("CWE-")
    pwd = os.path.abspath(os.path.dirname(__file__))
    pn = os.path.join(pwd, f"summary/CWE-{int(cwe[4:])}.txt")
    with open(pn) as f:
        return f.read()
    return ""

def load_cwe_title(cwe):
    assert cwe.startswith("CWE-")
    pwd = os.path.abspath(os.path.dirname(__file__))
    pn = os.path.join(pwd, "CWE.md")
    cwe_document = open(pn).read()

    pattern = re.compile(r'\b' + re.escape(cwe) + r': (.*?)\n')

    match = pattern.search(cwe_document)
    if match:
        return match.group(1).strip()
    else:
        return "CWE description not found."

def load_cwes():
    pwd = os.path.abspath(os.path.dirname(__file__))
    pn = os.path.join(pwd,"CWE.md")
    rtn = {}
    for line in open(pn, "rt"):
        line = line.strip()
        if len(line) == 0:
            continue
        cwe, desc = line.split(":")
        assert cwe.startswith("CWE-")
        cwe = normalize_cwe(cwe)
        desc = desc.strip()
        rtn[cwe] = desc
    return rtn

if __name__ == '__main__':
    assert normalize_cwe("cwe-123")  == "CWE-123"
    assert normalize_cwe("0123")     == "CWE-123"
    assert normalize_cwe("CWE 0123") == "CWE-123"
    assert normalize_cwe("CWE:123")  == "CWE-123"
