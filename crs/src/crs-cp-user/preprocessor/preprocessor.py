import os
import sys
import re
import json
import subprocess
from pathlib import Path, PurePosixPath
from argparse import ArgumentParser
from dataclasses import dataclass
import git
from tree_sitter import Language, Parser
import tree_sitter_c
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound
from .query import FunctionSummary, CCodeQuery
from .llm import OpenAIWrapper

# Some code borrowed from Aider

def isolate_code_helper(response, start, end):
    response = response.replace(', type: data', '')
    in_code = False
    build = []
    for line in response.split('\n'):
        if line.startswith(start):
            in_code = True
            continue
        elif line.startswith(end):
            in_code = False
            continue
        if in_code:
            build.append(line)
    if len(build) > 0:
        return '\n'.join(build)
    return response

class GitRepo:
    def __init__(self, fname):
        fname = Path(fname)
        fname = fname.resolve()

        if not fname.exists() and fname.parent.exists():
            fname = fname.parent

        try:
            repo_path = str(Path(git.Repo(fname, search_parent_directories=True).working_dir).resolve())
        except git.exc.InvalidGitRepositoryError:
            pass
        except git.exc.NoSuchPathError:
            pass

        self.repo = git.Repo(repo_path, odbt=git.GitDB)
        self.root = str(Path(self.repo.working_tree_dir).resolve())

    def normalize_path(self, path):
        return str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            commit = None

        files = []
        if commit:
            for blob in commit.tree.traverse():
                if blob.type == "blob":  # blob is a file
                    files.append(blob.path)

        # Add staged files
        index = self.repo.index
        staged_files = [path for path, _ in index.entries.keys()]

        files.extend(staged_files)

        # convert to appropriate os.sep, since git always normalizes to /
        res = set(self.normalize_path(path) for path in files)

        return res


def is_c_file(file_):
    return re.match(r'.*\.(c|cpp|cc)$', file_)

def build_history_prompt(files):
    build_list = ["<history>"]
    for fn in files:
        with open(fn) as f:
            build_list.append("<filename>")
            build_list.append(fn)
            build_list.append("</filename>")
            build_list.append("<content>")
            build_list.append(f.read())
            build_list.append("</content>")
    build_list.append("</history>")
    return '\n'.join(build_list)

class RepoTree:
    def __init__(self, harness, repo):
        self.harness = harness
        self.c_harness = harness
        # self.gitrepo = GitRepo(repo)
        # store tags for all files in repo (ones with definitions)
        # self.repo_files = self.gitrepo.get_tracked_files()
        self.repo = Path(repo)
        self.c_files = list(self.repo.rglob("*.c"))
        # just consider C stuff for now
        # self.c_files = [ (Path(self.gitrepo.root) / Path(f)).resolve() for f in self.repo_files if is_c_file(f) ]
        # self.c_files = [ (Path(repo) / Path(f)).resolve() for f in self.repo_files if is_c_file(f) ]
        print('\n'.join([str(f) for f in self.c_files]))
        # tag the defs
        # use pygments to get references
        self.definitions = {}
        self.llm = OpenAIWrapper('oai-gpt-4o')
        
    def get_all_definitions(self):
        # get definitions
        ccq = None
        for f in self.c_files:
            if not ccq:
                ccq = CCodeQuery(f)
            else:
                ccq.set_file(f)
            self.definitions[f] = ccq.get_function_signatures()
        
    def get_references(self, fname):
        with open(fname) as f:
            code = f.read()
        try:
            lexer = guess_lexer_for_filename(fname, code)
        except ClassNotFound:
            return

        tokens = list(lexer.get_tokens(code))
        # get_tokens rets (tokentype, value) https://pygments.org/docs/api/#pygments.lexer.Lexer.get_tokens
        all_defs = dict([(summary.name, summary) for summlist in self.definitions.values() for summary in summlist])
        tokens = set(token[1] for token in tokens if token[0] is Token.Name and token[1] in all_defs)
        references = [all_defs[token] for token in tokens]

        return references

    def get_root_references(self):
        self.get_all_definitions()
        return self.get_references(self.c_harness)
    
    def decide_on_harness(self):
        if is_c_file(self.harness):
            return self.harness
        with open(self.harness) as f:
            harness_code = f.read()

        history_files = []
        found = False
        found_file = self.harness
        max_ = 5
        i = 0

        # TODO filter by having main() or LLVMFuzzerTestOneInput()
        proc = subprocess.run(
            ['tree', '-P', '*.c|Makefile', self.gitrepo.root],
            text=True,
            capture_output=True
        )
        
        while not found and i < max_:
            messages = [
                {
                    'role': 'system',
                    'content': 'You are a code analysis helper that determines the first C entrypoint to a test suite'
                },
                {
                    'role': 'user',
                    'content': f'''The following is a non-C testing harness that feeds some data blob into a C program.
We need to figure out the first function in C that operates on the data blob.
<harness>
{harness_code}
</harness>

<directory-tree>
{proc.stdout}
</directory-tree>
                
{build_history_prompt(history_files)}

Respond with the following JSON response:
<json>
{{
    "found": false,
    "file": "Makefile"
}}
</json>
The JSON fields are
- "found": boolean, indicates whether the C file has been found
- "file": string, request to read this file. File is relative to {self.gitrepo.root}
If the last file in history looks correct, put true in "found" and the last file in "file".
Otherwise, put false in "found" and the next file that you want to read in "file".
You may request for files not yet in history.'''
                 }
            ]
            answer = self.llm.invoke(messages).content
            answer = isolate_code_helper(answer, '<json>', '</json>')
            answer = isolate_code_helper(answer, '```', '```')
            try:
                json_answer = json.loads(answer)
                found = json_answer['found']
                found_file = json_answer['file']
                found_file = str(Path(self.gitrepo.root) / found_file)
                history_files.append(found_file)
            except:
                pass
            i += 1
        self.c_harness = found_file
        return found_file
    
# TODO crawl for helpers for exemplars
    
""" target mock-cp
- provide build / make files and ask which file interacts with fuzzer
- provide list of C/C++ files and ask which ones to investigate
- grep for main().

Handle other build methods
https://github.com/google/oss-fuzz-gen/blob/main/experimental/c-cpp/build_generator.py
- makefile
- autoconf
- autogen
- bootstrap.sh
- cmakelists
"""

def run_preprocessor(target, source, workdir, output):
    target = Path(target).resolve()
    source = Path(source).resolve()
    output = Path(output).resolve()
    os.chdir(workdir)
    # harness, repo
    rt = RepoTree(str(target), str(source))
    c_entry = rt.decide_on_harness()
    refs = rt.get_root_references()
    ref_files = set([r.filename for r in refs])
    # print(ref_files)

    # just dump everything into one file
    # TODO format output and parse in reverser module
    build_list = []
    for ref in refs:
        build_list.append(ref.definition)
    with open(c_entry) as f:
        build_list.append(f.read())
    response = '\n'.join(build_list)
    with open(output, 'w') as f:
        f.write(response)
    # print(rt.llm.get_num_tokens_from_messages([{'role': 'user', 'content': response}]))
    # print(response)
            
if __name__ == '__main__':
    parser = ArgumentParser(
        description='Find C entrypoint and other relevant code'
    )
    parser.add_argument('--workdir', required=True, help='Working directory')
    parser.add_argument('--target', required=True, help='Path to target test harness')
    parser.add_argument('--source', required=True, help='Path to source code')
    parser.add_argument('--output', required=True, help='Path to output response')
    args = parser.parse_args()
    run_preprocessor(args.target, args.source, args.workdir, args.output)
