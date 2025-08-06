import atexit
import json
import os
import random
import re
import string
import time

from pathlib import Path
from collections import defaultdict
from typing import Any, Iterable, Mapping, Union

from loguru import logger

from .util import md5sum


ROOT = (Path(os.path.dirname(__file__)) / "../../").resolve()


def normalize_msg(msg):
    msg = msg.copy()

    if hasattr(msg, "model_dump"):
        msg = msg.model_dump()

    # heuristics to normalize msg
    if "tool_call_id" in msg:
        del msg["tool_call_id"]

    # fix random/host-specific path
    if "content" in msg:
        # replace /tmp/[...]/main.py => /tmp/[xxxx]/main.py
        pattern = r'(/tmp/workspace-)[a-zA-Z0-9_]+(/)'
        msg["content"] = re.sub(pattern, r'\1xxxxxxxx\2', msg["content"])

        # e.g., /home/taesoo/aixcc/crs-agi -> REPO_ROOT
        msg["content"] = msg["content"].replace(str(ROOT), "REPO_ROOT")

        # e.g., script name
        pattern = r'(/main-)[0-9_]+(\.py)'
        msg["content"] = re.sub(pattern, r'\1xxxx\2', msg["content"])
        pattern = r'(/script-)[0-9_]+(\.py)'
        msg["content"] = re.sub(pattern, r'\1xxxx\2', msg["content"])

        # e.g., 0xN
        pattern = r'(0x)[0-9a-f]+'
        msg["content"] = re.sub(pattern, r'0xNNNN', msg["content"])

    # enforce orders
    out = []
    for k in ["role", "name", "content"]:
        if k in msg:
            out.append("%s: %s" % (repr(k), repr(msg[k])))
    return "{%s}" % (", ".join(out))


def normalize_key(llm, msg):
    return "\n".join([
        llm.name, normalize_msg(msg), str(llm.temperature), str(llm.seed), str(llm.mode)
    ])


def normalize_plugins(llm):
    plugins = []
    if llm.plugins:
        plugins = tuple(llm.plugin_handlers.keys())
    return plugins


class RestoredCompletion(dict):
    pass


def dict_to_properties(data: Union[Mapping[str, Any], Iterable]) -> object:
    """
    Example
    -------
    >>> data = {
    ...     "name": "Bob Howard",
    ...     "positions": [{"department": "ER", "manager_id": 13}],
    ... }
    ... data_to_object(data).positions[0].manager_id
    13
    """

    if isinstance(data, dict):
        r = RestoredCompletion()
        for k, v in data.items():
            if type(v) is dict or type(v) is list:
                o = dict_to_properties(v)
                setattr(r, k, o)
                r[k] = o
            else:
                setattr(r, k, v)
                r[k] = v
        return r
    elif isinstance(data, list):
        return [dict_to_properties(e) for e in data]
    else:
        return data

def remove_all_keys(data, key):
    if isinstance(data, dict):
        r = {}
        for k, v in data.items():
            if k == key:
                continue
            if type(v) is dict or type(v) is list:
                r[k] = remove_all_keys(v, key)
            else:
                r[k] = v
        return r
    elif isinstance(data, list):
        return [remove_all_keys(e, key) for e in data]
    else:
        return data


#
# key -> (md5(parent), plugins, msg)
#
class Recorder:
    def __init__(self, pn=None):
        self.out = defaultdict(set)
        self.lasthash = None
        self.pn = pn

        atexit.register(self.__at_exit)

    def add(self, llm, msg, completion):
        plugins = normalize_plugins(llm)
        key = normalize_key(llm, msg)

        self.out[key].add((self.lasthash, plugins, self.normalize_completion(completion)))

        self.lasthash = md5sum(key)

    def normalize_completion(self, completion):
        out = remove_all_keys(completion.copy(), "id")
        del out["created"]

        return json.dumps(out)

    def save_to(self, pn):
        plain = {}
        if Path(pn).exists():
            content = open(pn).read()
            if len(content) != 0:
                plain.update(json.loads(content))

        # merge two dicts
        out = defaultdict(set)
        for d in [plain.items(), self.out.items()]:
            for (k, vs) in d:
                for (lasthash, plugins, completion) in vs:
                    out[k].add((lasthash, tuple(plugins), completion))

        # set to list for json decoder
        out = {k: list(v) for (k, v) in out.items()}

        with open(pn, "w") as fd:
            json.dump(out, fd, indent=4)

    def __at_exit(self):
        logger.info(f"Record saved to {self.pn}")
        if self.pn:
            self.save_to(self.pn)


class Replayer:
    def __init__(self, pn, seed=None):
        assert Path(pn).exists()

        if seed:
            random.seed(seed)

        db = defaultdict(set)
        for (k, vs) in json.load(open(pn)).items():
            for (lasthash, plugins, completion) in vs:
                db[k].add((lasthash, tuple(plugins), completion))
        self.db = db

        logger.info(f"Record restored from {pn}")

    def get(self, llm, lasthash, msg):
        key = normalize_key(llm, msg)
        if key in self.db:
            # seek exact match
            matched = []
            for (h, p, c) in self.db[key]:
                if lasthash == h:
                    matched.append((h, p, c))

            if len(matched) == 0:
                matched = list(self.db[key])

            # pick one randomly
            (h, p, c) = random.choices(matched)[0]

            # TODO. ignore plugins e.g., llm has all of the plugins in the db
            return (md5sum(key), self.restore_completion(c))

        print("%s" % repr(key))
        raise Exception(f"Failed to find a recorded prompt: lasthash={lasthash},key={key}")

    def restore_completion(self, c):
        def uuid(n):
            return "".join(random.choices(string.ascii_letters + string.digits, k=n))
        chatcmpl = "chatcmpl-%s" % uuid(29)

        # completion id
        c = json.loads(c)
        c["id"] = chatcmpl
        c["created"] = int(time.time())

        # tool id
        for i in range(len(c["choices"])):
            msg = c["choices"][i]["message"]
            if "tool_calls" in msg:
                tools = msg["tool_calls"]
                for j in range(len(tools)):
                    tools[j]["id"] = "call_%s" % uuid(24)

        return dict_to_properties(c)
