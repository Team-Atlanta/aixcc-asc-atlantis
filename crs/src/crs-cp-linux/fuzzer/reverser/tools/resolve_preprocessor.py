import subprocess
import os
import sys
import json
from tree_sitter import Language, Parser
import tree_sitter_c
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).parent.parent.resolve()
C_LANGUAGE = Language(tree_sitter_c.language())
parser = Parser()
parser.set_language(C_LANGUAGE)

def strip_comments(harness: str) -> str:
    harness_bytes = bytes(harness, 'utf-8')
    harness_tree = parser.parse(harness_bytes)
    query = C_LANGUAGE.query('''
        (comment) @comment
    ''')
    captures = query.captures(harness_tree.root_node)
    code_list = []
    previous_idx = 0
    # assume captures are sequential...
    for c, _ in captures:
        code_list.append(harness_bytes[previous_idx:c.start_byte])
        previous_idx = c.end_byte
    code_list.append(harness_bytes[previous_idx:])
    glue_bytes = b'\n'.join(code_list)
    return str(glue_bytes, 'utf-8')

def preprocess(data: bytes) -> bytes:
    result = subprocess.run(
        ['clang', '-E', '-'],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout

# Return the func node
def get_function(name: str, data: bytes):
    tree = parser.parse(data)
    query = C_LANGUAGE.query(f'''
        (function_definition
            declarator: (function_declarator
            declarator: (identifier) @id
            (#eq? @id {name}))) @func
    ''')
    captures = query.captures(tree.root_node)
    if len(captures) < 2: return None
    func, _ = captures
    return func[0]

def preprocessor_pass(name: str, harness: str):
    harness_bytes = bytes(harness, 'utf-8')
    expanded_bytes = preprocess(harness_bytes)
    harness_func = get_function(name, harness_bytes)
    expanded_func = get_function(name, expanded_bytes)
    if harness_func is None or expanded_func is None:
        return harness
    glued = harness_bytes[:harness_func.start_byte] + expanded_bytes[expanded_func.start_byte:expanded_func.end_byte] + harness_bytes[harness_func.end_byte:]
    return str(glued, 'utf-8')

def get_defines(harness: str):
    harness_bytes = bytes(harness, 'utf-8')
    tree = parser.parse(harness_bytes)
    query = C_LANGUAGE.query(f'''
        (preproc_def 
            name: (identifier) @id)
    ''')
    captures = query.captures(tree.root_node)
    if len(captures) < 1: return None
    constants = []
    for c, _ in captures:
        constant_str = str(harness_bytes[c.start_byte:c.end_byte], 'utf-8')
        constants.append(constant_str)
    return constants

def search_for_constants(node, harness_bytes, constant_bytes, collect):
    for c in constant_bytes:
        if c == harness_bytes[node.start_byte:node.end_byte]:
            collect.append((node, c))
    for n in node.children:
        search_for_constants(n, harness_bytes, constant_bytes, collect)

def get_switch_if_case(node):
    cursor = node
    look_for_switch = False
    while cursor is not None:
        if not look_for_switch and cursor.type == 'case_statement':
            look_for_switch = True
        elif look_for_switch and cursor.type == 'switch_statement':
            return cursor
        cursor = cursor.parent
    return None

def byte_idx_to_linum(idx, data):
    nl_byte = b'\n'
    lines = data.split(nl_byte)
    track = 0
    for (i, part) in enumerate(lines):
        # print(f'{i}, {part}')
        start = track
        end = track + len(part) + 1 # +1 for \n
        if idx >= start and idx < end:
            return i + 1 # linum starts with 1
        track = end
    return -1

def linum_to_byte_idx(linum, data):
    nl_byte = b'\n'
    lines = data.split(nl_byte)
    if linum - 1 >= len(lines) or linum <= 0:
        return -1
    track = 0
    for part in lines[:linum]:
        track += len(part)
    return track
        
# TODO check for entire file!
def get_constants_linums(name, harness, constants):
    harness_bytes = bytes(harness, 'utf-8')
    tree = parser.parse(harness_bytes)
    query = C_LANGUAGE.query(f'''
        (function_definition
            declarator: (function_declarator
            declarator: (identifier) @id
            (#eq? @id {name}))) @func
    ''')
    captures = query.captures(tree.root_node)
    if len(captures) < 2: return None
    func, _ = captures
    func_bytes = harness_bytes[func[0].start_byte:func[0].end_byte]
    func_tree = parser.parse(harness_bytes)
    func_root = func_tree.root_node
    constant_bytes = [bytes(c, 'utf-8') for c in constants]
    collect = []
    search_for_constants(func_root, harness_bytes, constant_bytes, collect)
    linums = set()
    for (node, cb) in collect:
        switch_opt = get_switch_if_case(node)
        if switch_opt:
            switch_idx = switch_opt.start_byte
            linums.add(byte_idx_to_linum(switch_idx, harness_bytes))
    return linums

def patch_harness_cases(harness, cases):
    harness_bytes = bytes(harness, 'utf-8')
    tree = parser.parse(harness_bytes)
    for case in cases:
        query = C_LANGUAGE.query(f'''
            (case_statement) @case
        ''')
        captures = query.captures(tree.root_node)
        for cap, _ in captures:
            if len(cap.children) < 4:
                continue
            # print(cap.children)
            case_value = cap.children[1] # thing after case keyword
            case_succ = cap.children[3] # thing after colon
            cap_linum = byte_idx_to_linum(case_succ.start_byte, harness_bytes)
            # print(case_value)
            if abs(cap_linum - case['line']) <= 1:
                # new_value = bytes(str(harness_bytes[case_value.start_byte:case_value.end_byte]), 'utf-8')
                new_value = bytes(str(case['value']), 'utf-8')
                harness_bytes = harness_bytes[:case_value.start_byte] + new_value + harness_bytes[case_value.end_byte:]
                # TODO optimization, need to find the API doc
                # tree.edit(
                #     start_byte=case_value.start_byte,
                #     old_end_byte=case_value.end_byte,
                #     new_end_byte=case
                # )
                tree = parser.parse(harness_bytes)
                break
    return str(harness_bytes, 'utf-8')

def switch_case_constant_patch(harness):
    # create tmp directory, assume we've already chdir'd to workdir
    with TemporaryDirectory(dir='.') as tmp_dir:

        LINE_FILE = Path(tmp_dir) / 'preprocessor_cases.txt'
        RESULTS_FILE = Path(tmp_dir) / 'results.json'
        HARNESS_FILE = Path(tmp_dir) / 'harness.c'

        with open(HARNESS_FILE, 'w') as hf:
            hf.write(harness)

        constants = get_defines(harness)
        if constants is None or len(constants) == 0:
            print("no constants")
            return harness

        linums = get_constants_linums('harness', harness, constants)
        if linums is None or len(linums) == 0:
            print("no linums")
            return harness

        with open(LINE_FILE, 'w') as f:
            f.write('\n'.join([str(l) for l in linums]))

        # build if necessary
        check_build = lambda: (ROOT / 'static/install').is_dir() and (ROOT / 'static/build').is_dir()  and (ROOT / 'static/install/run_macros.sh').is_file()
        if not check_build():
            print('building')
            result = subprocess.run(['./build.sh'], 
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    cwd=(ROOT / 'static'))

        # if build fails
        if not check_build():
            print('no build')
            return harness

        # call run_macros
        result = subprocess.run(['./run_macros.sh', Path(tmp_dir).resolve(), HARNESS_FILE.resolve(), LINE_FILE.resolve(), RESULTS_FILE.resolve()], 
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                cwd=(ROOT / 'static/install'))
        try:
            with open(RESULTS_FILE) as f:
                cases = json.loads(f.read())
        except:
            print("no results")
            return harness
        patched = patch_harness_cases(harness, cases)
        return patched

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        harness_path = sys.argv[1]
    else:
        harness_path = Path(__file__).parent.parent / 'test_harnesses/NRFIN-00001.c'
    with open(harness_path) as f:
        harness = f.read()
    patched = preprocessor_pass('harness', harness)
    patched = switch_case_constant_patch(patched)
    patched = strip_comments(patched)
    print(patched)
