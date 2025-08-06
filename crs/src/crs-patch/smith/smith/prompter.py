from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from .bug import Bug, Location
from .challenge import BuildInfo
from .code_analyzer import FunctionInfo
from .language import get_language

logger = logging.getLogger(__name__)

class Prompt():
    def __init__(self):
        # Don't add new fields here. Add them to the `aux` dictionary.
        self.header = []
        self.footer = []
        self.aux = {}

    def to_string(self):
        return ''.join(self.header)

class Template():
    def __init__(self):
        self.header = []
        self.footer = []

    def to_string(self, body: str):
        return ''.join(self.header) + body + ''.join(self.footer)

    def render(self, body: str):
        return ''.join(self.header) + body + ''.join(self.footer)

class PromptManager():
    def __init__(self):
        self.prompt = Prompt()
        self.template = Template()

    def update(self, bug: Bug, updaters: List["PromptUpdater"]):
        for updater in updaters:
            updater.update(bug, self.prompt, self.template)

    def get_prompt_as_string(self):
        return self.prompt.to_string()

    def finalize(self, output: str):
        return self.template.to_string(output)

def find_function(location: Location, build_info: Optional[BuildInfo]) -> FunctionInfo:
    lang = get_language(location.src)

    analyzer = lang.get_analyzer(location.src, build_info)
    return analyzer.find_function((location.start, location.end))

def find_functions(bug: Bug, build_info: Optional[BuildInfo]) -> List[FunctionInfo]:
    functions = []
    for location in bug.locations:
        try:
            functions.append(find_function(location, build_info))
        except Exception: # pylint: disable=broad-exception-caught
            logger.warning(f"Failed to find function in {location}")
            continue
    return functions

class PromptUpdater(ABC):
    @abstractmethod
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        raise NotImplementedError

class LanguageSpecifier(PromptUpdater):
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        lang = bug.get_language()

        writer = lang.get_writer()
        writer.append_comment(lang.name, indenting=True)

        # e.g., // C
        prompt.header += writer.flush()

class VulnerableFunctionNotifier(PromptUpdater):
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        lang = get_language(bug.locations[0].src)
        assert bug.challenge is not None
        vulnerable_functions = find_functions(bug, bug.challenge.build_info)

        assert len(vulnerable_functions) > 0, "No vulnerable function found"
        # TODO: Support multiple vulnerable functions
        # assert len(vulnerable_functions) == 1, "Multiple vulnerable functions are not supported"

        src = vulnerable_functions[0].src
        start = vulnerable_functions[0].start
        end = vulnerable_functions[0].end

        lines = open(src, encoding='utf-8').readlines()
        writer = lang.get_writer(lines[start])
        # +1 is needed because CodeAnalyzer returns line no. of end token
        writer.append_comment(*lines[start: end + 1], indenting=True)
        writer.append("\n", indenting=True)
        writer.append_comment("FIXED VERSION:\n", indenting=True)

        # TODO: This is a hacky way to get the function definition
        for i in range(start, end):
            if "{" in lines[i]:
                function_def = ''.join(lines[start:i+1])
                break

        prompt.aux["function_def"] = function_def.strip()
        prompt.header += ["\n"] + writer.flush() + [function_def]
        template.header += [function_def]

class ChainOfThoughtPreambleUpdater(PromptUpdater):
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        prompt.header = ['Q.\n'] + prompt.header
        prompt.header += ['\nA.\nLet\'s think step by step.\n']

class CWEHeaderUpdater(PromptUpdater):
    def __init__(self, verbose: bool):
        self.verbose = verbose

    def update(self, bug: Bug, prompt: Prompt, template: Template):
        cwe = bug.cwes[0]
        lang = get_language(bug.locations[0].src)

        writer = lang.get_writer()
        writer.append_comment(f"BUG: {cwe.name}\n", indenting=True)
        if self.verbose:
            # handle multi-line descriptions
            for line in f'MESSAGE: {cwe.desc}'.split('\n'):
                writer.append_comment(line + '\n', indenting=True)

        prompt.header += writer.flush()

def get_crash_log(bug: Bug) -> Optional[str]:
    if bug.challenge is None:
        return None

    return bug.challenge.crash_analyzer.get_crash_log().decode()

class CrashLogUpdater(PromptUpdater):
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        assert bug.challenge is not None
        crash_log = get_crash_log(bug)
        assert crash_log is not None
        lang = get_language(bug.locations[0].src)

        writer = lang.get_writer()
        writer.append_comment("CRASH LOG:\n", indenting=True)
        # TODO: Parse crash log and preprocess it? e.g., stack trace
        writer.append_comment(crash_log, indenting=True)

        prompt.header += writer.flush()

class FunctionRetrospector(PromptUpdater):
    def __init__(self, trim: bool = False):
        self.trim = trim

    def update(self, bug: Bug, prompt: Prompt, template: Template):
        assert bug.challenge is not None
        vulnerable_functions = find_functions(bug, bug.challenge.build_info)

        if len(vulnerable_functions) == 0:
            raise ValueError("No vulnerable function found")
        # TODO: Support multiple vulnerable functions
        # assert len(vulnerable_functions) == 1, "Multiple vulnerable functions are not supported"

        src = vulnerable_functions[0].src
        start = vulnerable_functions[0].start
        end = vulnerable_functions[0].end

        # Add previous lines to the prompt & template
        lines = open(src).readlines()
        if not self.trim:
            prompt.header += lines[:start]

        template.header += lines[:start]
        # +1 is needed because CodeAnalyzer returns line no. of end token
        template.footer += self._sanitize_footer(lines[end + 1:])

    def _sanitize_footer(self, lines: List[str]) -> List[str]:
        # TODO: Enable this one only for java
        for i, line in enumerate(lines):
            # In Java, the function definition can be included in the class definition
            if line.strip() != "}":
                return lines[i:]

        return []

class DefScraper(PromptUpdater):
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        lang  = get_language(bug.locations[0].src)

        if lang.name not in ['C', 'C++']:
            logger.warning(f"Language {lang.name} is not supported.")
            raise NotImplementedError

        writer = lang.get_writer()
        assert bug.challenge is not None
        vulnerable_functions = find_functions(bug, bug.challenge.build_info)

        assert len(vulnerable_functions) > 0, "No vulnerable function found"
        # TODO: Support multiple vulnerable functions
        # assert len(vulnerable_functions) == 1, "Multiple vulnerable functions are not supported"

        src = vulnerable_functions[0].src
        lines = open(src).readlines()

        for i, line in enumerate(lines):
            if line.startswith("#define"):
                writer.append(lines[i])
                # for j in range(i, len(lines)):
                #     if lines[j].strip().endswith("\\"): pass
                #     else:
                #         break
                # writer.append(''.join(lines[i:j+1])+'\n')

        prompt.header += writer.flush()

class GlobalsScraper(PromptUpdater):
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        lang  = get_language(bug.locations[0].src)

        if lang.name not in ['C', 'C++']:
            logger.warning(f"Language {lang.name} is not supported.")
            raise NotImplementedError

        writer = lang.get_writer()
        assert bug.challenge is not None
        vulnerable_functions = find_functions(bug, bug.challenge.build_info)

        assert len(vulnerable_functions) > 0, "No vulnerable function found"
        # TODO: Support multiple vulnerable functions
        # assert len(vulnerable_functions) == 1, "Multiple vulnerable functions are not supported"

        src = vulnerable_functions[0].src
        lines = open(src).readlines()

        # XXX: Too hacky.
        for line in lines:
            if "/*" in line and "*/" in line:
                line = line.split("/*")[0] + line.split("*/")[1]
            if "//" in line:
                line = line.split("//")[0]
            line = line.strip()
            if line.startswith("static") and line.endswith(";"):
                writer.append(line+"\n")

        prompt.header += writer.flush()

class ZeroShotFunctionNotifier(PromptUpdater):
    def __init__(self, token: bool = True):
        self.token = token

    def update(self, bug: Bug, prompt: Prompt, template: Template):
        lang = bug.get_language()

        if lang.name not in ['C', 'C++']:
            logger.warning(f"Language {lang.name} is not supported.")
            raise NotImplementedError

        src = bug.locations[0].src
        # -1 to match index starting from 0
        bug_start = bug.locations[0].start - 1
        bug_end = bug.locations[0].end - 1

        assert bug.challenge is not None
        func = find_function(bug.locations[0], bug.challenge.build_info)
        func_start = func.start
        func_end = func.end

        lines = open(src).readlines()

        # Copy the lines before the bug start
        writer = lang.get_writer()
        writer.append(*lines[func_start:bug_start])

        # This part is the same as CWEHeaderUpdater.
        # Maybe this can be refactored to a common function.
        cwe = bug.cwes[0]
        writer.append_comment(
            f"BUG: {cwe.name}\n",
            *lines[bug_start: bug_end + 1],
            "FIXED:\n",
            indenting=True,
            block=True)

        writer.append("\n", indenting=True)

        if self.token:
            # Append the first token of vulnerable part so that the LLM returns code.
            first_token = ""
            for i in range(bug_start, bug_end + 1):
                split = lines[i].strip().split()
                if len(split) > 0:
                    # If the line is a comment, then it is not the first token.

                    # TODO: The get_line_comment_symbol only returns a single type.
                    #       Might need to change this to a list of comment tokens.

                    if not writer.get_line_comment_symbol() in split[0]:
                        first_token = split[0]
                        break

            writer.append(first_token, indenting=True)

        prompt.header += ["\n"] + writer.flush()
        prompt.footer = lines[bug_end + 1:func_end + 1]
        template.header += ["\n"] + writer.flush()
        template.footer.insert(0, "\n")

class GoogleFunctionNotifier(PromptUpdater):
    def update(self, bug: Bug, prompt: Prompt, template: Template):
        lang = bug.get_language()

        if lang.name not in ['C', 'C++']:
            logger.warning(f"Language {lang.name} is not supported.")
            raise NotImplementedError

        src = bug.locations[0].src
        bug_start = bug.locations[0].start - 1 # -1 to match index starting from 0

        assert bug.challenge is not None
        func = find_function(bug.locations[0], bug.challenge.build_info)
        func_start = func.start
        func_end = func.end

        lines = open(src).readlines()

        writer = lang.get_writer(lines[func_start])
        writer.append(*lines[func_start:bug_start])

        # This part is the same as CWEHeaderUpdater.
        # Maybe this can be refactored to a common function.
        cwe = bug.cwes[0]
        writer.append_comment(
            f"Please fix the <{cwe.name}> error originating here.\n",
            indenting=True)
        # for line in f'MESSAGE: {cwe.desc}'.split('\n'):
        #     writer.append_comment(line + '\n')

        writer.append(*lines[bug_start: func_end+1])

        prompt.header += ["\n"] + writer.flush()
        prompt.aux["original_body"] = lines[func_start:func_end + 1]
