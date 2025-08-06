import os
import hashlib
import traceback
import json

from collections import deque

# hash() is not persistent anymore in python
def md5sum(content):
    m = hashlib.md5()
    m.update(content.encode())
    return m.hexdigest()


def walk_breadth_first(root_dir, ignore_dirs, ignore_exts):
    """
    Walk over a given directory in a breadth-first manner and yield a list of files, 
    ignoring specified directories and file extensions.

    :param root_dir: The root directory to start walking.
    :param ignore_dirs: A list of directory names to ignore.
    :param ignore_exts: A list of file extensions to ignore.
    """
    queue = deque([root_dir])
    while queue:
        current_dir = queue.popleft()

        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    if entry.is_dir() and entry.name in ignore_dirs:
                        continue
                    full_path = entry.path
                    if entry.is_dir():
                        queue.append(full_path)
                    elif entry.is_file():
                        if any(full_path.endswith(ext) for ext in ignore_exts):
                            continue
                        yield full_path
        except PermissionError:
            continue  # Skip directories where permission is denied


# from aider
def cvt(s):
    if isinstance(s, str):
        return s
    try:
        return json.dumps(s, indent=4)
    except TypeError:
        return str(s)

def dump(*vals):
    # http://docs.python.org/library/traceback.html
    stack = traceback.extract_stack()
    vars = stack[-2][3]

    # strip away the call to dump()
    vars = "(".join(vars.split("(")[1:])
    vars = ")".join(vars.split(")")[:-1])

    vals = [cvt(v) for v in vals]
    has_newline = sum(1 for v in vals if "\n" in v)
    if has_newline:
        print("%s:" % vars)
        print(", ".join(vals))
    else:
        print("%s:" % vars, ", ".join(vals))
