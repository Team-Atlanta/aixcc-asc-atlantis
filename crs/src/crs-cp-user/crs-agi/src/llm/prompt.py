import copy
import json
import os

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from mako.template import Template

ROOT = Path(os.path.dirname(__file__))
PROMPTS = ROOT / "../prompts"


@dataclass
class Toolcall:
    function: str
    arguments: dict[str, str]
    result: str


class Prompt:
    """OpenAI-compatible prompt for LiteLLM."""

    def __init__(self):
        self._prompt = []

    def get(self):
        """Get the final formatted prompt."""

        return self._prompt

    def append(self, content: str, role: Optional[str] = None):
        """Add a message with a specified role."""

        role = role or "user"

        assert role in ["system", "assistant", "user", "tool"]

        self._prompt.append({
          'role': role,
          'content': content,
        })

    def append_raw(self, raw: dict):
        """Add a raw message to the prompt."""

        self._prompt.append(raw)

    def append_tool_result(self, call, result):
        """Add a tool message to the prompt."""

        self._prompt.append({
            "tool_call_id": call.id,
            "role": "tool",
            "name": call.function.name,
            "content": result,
        })

    def copy(self):
        """Copy me."""

        return copy.deepcopy(self)

    def store_to(self, pn):
        with open(pn, "w") as fd:
            for msg in self._prompt:
                if hasattr(msg, "model_dump"):
                    msg = msg.model_dump()
                fd.write(json.dumps(msg, indent=4))
                fd.write("\n")

    def pop(self, n=1):
        for _ in range(n):
            if len(self._prompt) != 0:
                self._prompt.pop()

    def len(self):
        return len(self._prompt)

    def get_all_toolcalls(self):
        orders = []
        toolcalls = {}

        for p in self._prompt:
            if hasattr(p, "model_dump"):
                p = p.model_dump()

            if "tool_calls" in p:
                for t in p["tool_calls"]:
                    try:
                        args = json.loads(t["function"]["arguments"])
                    except json.decoder.JSONDecodeError:
                        args = {"code" : t["function"]["arguments"]}

                    orders.append(t["id"])
                    toolcalls[t["id"]] = \
                        Toolcall(function=t["function"]["name"],
                                 arguments=args,
                                 result=None)
                continue

            if "tool_call_id" in p:
                toolcalls[p["tool_call_id"]].result = p["content"]

        return [toolcalls[id] for id in orders]


class PromptTemplate:
    def __init__(self):
        self.kw = {}
        self.template = None

    def build(self, pn):
        return self.builds(open(PROMPTS / pn).read())

    def builds(self, template):
        self.template = Template(template, module_directory=PROMPTS)
        return self

    def add(self, **kw):
        self.kw.update(kw)
        return self

    def render(self, **kw):
        self.kw.update(kw)
        return self.template.render(**self.kw)


def load_prompt(pn, **kw):
    return PromptTemplate().build(pn).render(**kw)
