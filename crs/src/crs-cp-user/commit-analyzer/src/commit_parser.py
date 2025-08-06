import re
import subprocess

import logging
import tempfile

from cparser import CCodeAnalyzer  # type: ignore
from javaparser import JavaCodeAnalyzer
from pathlib import Path

from typing import List, Literal, Generator
from dataset import FunctionChange, CommitChange, FileChange


class CommitParser:
    path = ""

    def __init__(self, path, refs) -> None:
        self.path = path
        self.logger = logging.getLogger("CommitParser")
        # self.checkout_branch(refs)

    def checkout_branch(self, refs):
        cmd = ["git", "-C", self.path, "checkout", refs]
        # subprocess.run(cmd, stdout=subprocess.PIPE, text=True, errors="ignore")

    def get_changed_files(self, diff):
        regx_filename = "[\w\./\-,\+]+"
        pattern = rf"index \w+\.\.\w+.*\n--- (a/|)({regx_filename})\n\+\+\+ (b/|)({regx_filename})\n@@"
        matches = re.findall(pattern, diff)

        if len(matches) != len(set(matches)):
            self.logger.error(diff)
            self.logger.exception(
                "Duplicate matches found in patch. Diff assumption failed."
            )
        return set(matches)

    def get_diff(self, commit_sha):
        cmd = [
            "git",
            "-C",
            self.path,
            "log",
            commit_sha,
            "-n",
            "1",
            "-p",
            "--pretty=format:",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, errors="ignore")

        return proc.stdout

    def parse_code(self, code: str, lang: Literal["c", "java"]):
        with tempfile.NamedTemporaryFile(suffix=".c") as f:
            f.write(code.encode())
            f.flush()
            path = Path(f.name)

            try:
                if lang == "c":
                    analyzer = CCodeAnalyzer(path, [])
                    analyzer.initialize()

                    # Remain only defined in the target file not headers
                    decls = (
                        analyzer._declarations["FUNCTION_DECL"]
                        if "FUNCTION_DECL" in analyzer._declarations
                        else {}
                    )
                    decls = {
                        name: body for name, body in decls.items() if body.file == path
                    }

                elif lang == "java":
                    analyzer = JavaCodeAnalyzer(path)
                    decls = analyzer.get_all_functions()
                else:
                    self.logger.error(f"Unsupported language {lang}")
                    decls = {}
            except Exception as e:
                self.logger.error(f"Error while code analyzing: {e}")
                return {}
        return decls

    def get_commits(self, skip: int = 0, n: int = 100):
        command = [
            "git",
            "-C",
            self.path,
            "log",
            "--skip",
            str(skip),
            "-n",
            str(n),
            "--pretty=format:%H",
        ]
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, text=True, errors="ignore"
        )

        return proc.stdout.split("\n")

    def get_subject(self, commit):
        command = ["git", "-C", self.path, "log", "-1", "--format=%s", commit]
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, text=True, errors="ignore"
        )

        return proc.stdout

    def get_file_content(self, commit, file):
        command = ["git", "-C", self.path, "show", f"{commit}:{file}"]
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, text=True, errors="ignore"
        )

        return proc.stdout

    def get_parent_commit(self, commit):
        command = ["git", "-C", self.path, "log", "--pretty=%P", "-n", "1", commit]
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, text=True, errors="ignore"
        )

        return proc.stdout.split("\n")[0]

    def get_func_info(self, commit, filepath, lang: Literal["c", "java"]):
        if filepath == "/dev/null":
            return dict()
        new_code = self.get_file_content(commit, filepath)
        new_functions = self.parse_code(new_code, lang)

        return new_functions

    def parse_repo(
        self, analyze_unit
    ) -> Generator[
        List[FunctionChange] | List[FileChange] | List[CommitChange], None, None
    ]:
        analyze_unit = analyze_unit
        if analyze_unit not in ["commit", "file", "function"]:
            analyze_unit = "file"
            self.logger.exception(
                f"Invalid analyze unit {analyze_unit}. Defaulting to commit"
            )

        skip = 0
        n = 100
        while True:
            commits = self.get_commits(skip, n)
            if not commits or commits[0] == "":
                break
            function_changes = []
            results = []
            for commit in commits:
                subject = self.get_subject(commit)
                if subject.startswith("[IGNORE]"):
                    continue

                parent_commit = self.get_parent_commit(commit)
                if parent_commit == "":
                    break

                diff = self.get_diff(commit)
                changed_files = self.get_changed_files(diff)

                for changed_file in changed_files:
                    old_file = changed_file[1]
                    new_file = changed_file[3]
                    # TODO need to handle other file types if java analysis is needed
                    if new_file.endswith((".c", ".h")):
                        lang = "c"
                    elif new_file.endswith(".java"):
                        lang = "java"
                    else:
                        self.logger.warning(
                            f"Skipping {new_file} as its unsupported extension"
                        )
                        continue

                    new_functions = self.get_func_info(commit, new_file, lang)
                    old_functions = self.get_func_info(parent_commit, old_file, lang)

                    all_functions = set(new_functions.keys()) | set(
                        old_functions.keys()
                    )

                    for func in all_functions:
                        new_code_info = new_functions.get(func, None)
                        old_code_info = old_functions.get(func, None)

                        new_code = (
                            new_code_info.code if new_code_info is not None else ""
                        )
                        old_code = (
                            old_code_info.code if old_code_info is not None else ""
                        )

                        # Only consider function changes
                        # TODO need to handle other changes if global variable changes matter
                        if new_code != old_code:
                            function_change = FunctionChange(
                                commit, func, old_code, new_code, old_file, new_file
                            )
                            if analyze_unit == "function":
                                results.append(function_change)
                            else:
                                function_changes.append(function_change)

                    if analyze_unit == "file" and len(function_changes) > 0:
                        commit_change = FileChange(commit, function_changes)
                        results.append(commit_change)
                        function_changes = []

                if analyze_unit == "commit" and len(function_changes) > 0:
                    commit_change = CommitChange(commit, function_changes)
                    results.append(commit_change)
                    function_changes = []

            yield results
            skip += 100
