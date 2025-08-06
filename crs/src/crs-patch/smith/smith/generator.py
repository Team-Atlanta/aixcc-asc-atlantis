import logging
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Callable, List, Optional, Tuple, Type
from pathlib import Path

from typing_extensions import override

from .patch_trial import PatchTrial, PatchOutcome, PatchMeta
from .prompter import Prompt, Template
from .prompter import (
    PromptUpdater,
    LanguageSpecifier,
    FunctionRetrospector,
    VulnerableFunctionNotifier,
    CWEHeaderUpdater,
    CrashLogUpdater,
    DefScraper,
    GlobalsScraper,
    ZeroShotFunctionNotifier,
    GoogleFunctionNotifier,
 )
from .plugin import (
    plugin_read_func_source_code,
    plugin_read_global_var_source_code,
    plugin_read_struct_source_code
)
from .extractor import (
    CodeExtractor,
    FunctionDefExtractor,
    ZeroshotExtrapolator,
    GoogleExtrapolator
)
from .instructions import (
    OPENAI_SYSTEM_MESSAGE,
    OPENAI_SYSTEM_MESSAGE_FEWSHOT,
    OPENAI_SYSTEM_MESSAGE_ZEROSHOT,
    PROMPT_EVOLVE
)
from .bug import Bug
from .prompter import find_function
from .model import Dialog
from .agents.aider_agent import AiderAgent
from .agents.swe_agent import SWEAgent

logger = logging.getLogger(__name__)

class Generator(ABC):
    @staticmethod
    @abstractmethod
    def name() -> str:
        pass

    def __init__(self, challenge, bug, model, num_samples):
        self._challenge = challenge
        self._bug = bug
        self._model = model
        self._num_samples = num_samples

    @abstractmethod
    def generate_prompt(self) -> Tuple[Prompt, Template]:
        pass

    @abstractmethod
    def generate(self) -> List[PatchTrial]:
        pass

    @abstractmethod
    def evolve_prompt(self, trial: PatchTrial, outcome: PatchOutcome) -> Tuple[Prompt, Template]:
        pass

    @abstractmethod
    def evolve(self, trial: PatchTrial, outcome: PatchOutcome) -> Optional[PatchTrial]:
        pass

class LocalGenerator(Generator):
    @staticmethod
    @abstractmethod
    def updaters() -> List[PromptUpdater]:
        pass

    @staticmethod
    @abstractmethod
    def extractor() -> CodeExtractor:
        pass

    @staticmethod
    @abstractmethod
    def initial_dialog() -> str:
        pass

    @override
    def generate_prompt(self) -> Tuple[Prompt, Template]:
        prompt = Prompt()
        template = Template()

        for updater in self.updaters():
            updater.update(self._bug, prompt, template)

        return prompt, template

    @override
    def generate(self) -> List[PatchTrial]:
        prompt, template = self.generate_prompt()
        dialog = self._model.initiate_dialog(self.initial_dialog())
        dialog = dialog.add_user_message(prompt.to_string())

        # TODO: Currently only for C, support others
        # TODO: Move this to main.py?
        if self._model.use_plugins:
            analyzer = self._bug.get_language().get_analyzer(
                self._bug.src,
                self._bug.challenge.build_info) # build info?
            self._model.install_plugins([
                    plugin_read_func_source_code(analyzer.get_func_code),
                    plugin_read_struct_source_code(analyzer.get_struct_code),
                    plugin_read_global_var_source_code(analyzer.get_global_var_code)
                    ])

        responses = self._model.query(dialog, self._num_samples)
        results = []

        for response in responses:
            try:
                code = self.extractor().extract(response, prompt)
            except ValueError:
                # Or maybe just continue?
                code = "DUMMY-CODE"
            _program = template.render(code)
            current_dialog = dialog.add_assistant_message(response)
            trial = PatchTrial(
                bug=self._bug,
                dialog=current_dialog,
                prompt=prompt,
                template=template,
                # TODO: Fix to use correct diff parameter if LocalGenerator is used
                diff="",
                meta=PatchMeta(self._model.name(), 0.0),
                op="generate"
            )
            results.append(trial)

        return results

    @override
    def evolve_prompt(self, trial: PatchTrial, outcome: PatchOutcome) -> Tuple[Prompt, Template]:
        prompt = Prompt()
        prompt.header += f"No, it's wrong. I got this error: {outcome.message}\n"
        prompt.header += "Try again.\n"
        # prompt.header += " Always and only return the rewritten code, "
        # prompt.header += "without triple-backticks and function definition line.\n"
        return prompt, trial.template

    @override
    def evolve(self, trial: PatchTrial, outcome: PatchOutcome) -> Optional[PatchTrial]:
        prompt, template = self.evolve_prompt(trial, outcome)

        new_dialog = trial.dialog.add_user_message(prompt.to_string())
        response, = self._model.query(new_dialog, 1) # returns only one response

        try:
            code = self.extractor().extract(response, trial.prompt)
        except ValueError:
            logger.info(f"Failed to extract code from the response in trial {trial.name}")
            logger.debug(response)
            return None
        _program = template.render(code)

        # TODO: Fix to use correct diff parameter if LocalGenerator is used
        new_trial = PatchTrial.spawn(trial, new_dialog, "", "evolve")
        return new_trial

class DefaultPromptGenerator(LocalGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "default"

    @override
    @staticmethod
    def updaters() -> List[PromptUpdater]:
        return [
            LanguageSpecifier(),
            FunctionRetrospector(),
            CWEHeaderUpdater(verbose=True),
            VulnerableFunctionNotifier(),
            # ChainOfThoughtPreambleUpdater(),
        ]

    @override
    @staticmethod
    def extractor() -> CodeExtractor:
        return FunctionDefExtractor()

    @override
    @staticmethod
    def initial_dialog() -> str:
        return OPENAI_SYSTEM_MESSAGE

class CrashLogPromptGenerator(LocalGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "crash_log"

    @override
    @staticmethod
    def updaters() -> List[PromptUpdater]:
        return [
            LanguageSpecifier(),
            FunctionRetrospector(),
            CWEHeaderUpdater(verbose=True),
            CrashLogUpdater(),
            VulnerableFunctionNotifier(),
            # ChainOfThoughtPreambleUpdater(),
        ]

    @override
    @staticmethod
    def extractor() -> CodeExtractor:
        return FunctionDefExtractor()

    @override
    @staticmethod
    def initial_dialog() -> str:
        return OPENAI_SYSTEM_MESSAGE

class SingleFunctionPromptGenerator(LocalGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "single"

    @override
    @staticmethod
    def updaters() -> List[PromptUpdater]:
        return [
            LanguageSpecifier(),
            FunctionRetrospector(trim=True),
            DefScraper(),
            GlobalsScraper(),
            CWEHeaderUpdater(verbose=True),
            VulnerableFunctionNotifier(),
            # ChainOfThoughtPreambleUpdater(),
        ]

    @override
    @staticmethod
    def extractor() -> CodeExtractor:
        return FunctionDefExtractor()

    @override
    @staticmethod
    def initial_dialog() -> str:
        return OPENAI_SYSTEM_MESSAGE

class ZeroShotPromptGenerator(LocalGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "zeroshot"

    @override
    @staticmethod
    def updaters() -> List[PromptUpdater]:
        return [
            LanguageSpecifier(),
            FunctionRetrospector(trim=True),
            DefScraper(),
            # GlobalsScraper(),
            ZeroShotFunctionNotifier(),
        ]

    @override
    @staticmethod
    def extractor() -> CodeExtractor:
        return ZeroshotExtrapolator()

    @override
    @staticmethod
    def initial_dialog() -> str:
        return OPENAI_SYSTEM_MESSAGE_ZEROSHOT

class ZeroShotNoTokenPromptGenerator(LocalGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "zeroshot-notoken"

    @override
    @staticmethod
    def updaters() -> List[PromptUpdater]:
        return [
            LanguageSpecifier(),
            FunctionRetrospector(trim=True),
            DefScraper(),
            # GlobalsScraper(),
            ZeroShotFunctionNotifier(token=False),
        ]

    @override
    @staticmethod
    def extractor() -> CodeExtractor:
        return ZeroshotExtrapolator()

    @override
    @staticmethod
    def initial_dialog() -> str:
        return OPENAI_SYSTEM_MESSAGE_ZEROSHOT

class GooglePromptGenerator(LocalGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "google"

    @override
    @staticmethod
    def updaters() -> List[PromptUpdater]:
        return [
            LanguageSpecifier(),
            FunctionRetrospector(),
            GoogleFunctionNotifier(),
        ]

    @override
    @staticmethod
    def extractor() -> CodeExtractor:
        return GoogleExtrapolator()

    @override
    @staticmethod
    def initial_dialog() -> str:
        return OPENAI_SYSTEM_MESSAGE_FEWSHOT

class AgentError(Exception):
    pass

class AgentGenerator(Generator):
    def _emit_simple_vulnerability_info_snippet(self, bug: Bug) -> str:
        cwe = bug.cwes[0]
        func = find_function(bug.locations[0], None) # TODO: No build_info is okay?

        assert func.name is not None
        return f"Fix the '{cwe.name}' vulnerability in `{func.name}` function"

    def _emit_full_bic_snippet(self, bug_class: str, bic_diff: str) -> str:
        return (
            f"Fix the '{bug_class}' vulnerability introduced after the following commit:"
            f"\n\n```\n{bic_diff}\n```\n"
        )

    def _emit_calltrace_frame_snippet(self, frame, width=10) -> str:
        content = f"Function: {frame.func_name}\n"
        content += f"File: {frame.file}\n"

        lines = Path(frame.file).read_text(errors='replace').splitlines()

        for i, line in enumerate(lines, start=1):
            if i > frame.line - width and 'Pre-Context:' not in content:
                content += "Pre-Context:\n"
            elif i == frame.line:
                content += "Call Line:\n"
            elif i == frame.line + 1:
                content += "Post-Context:\n"

            if i > frame.line - width and i < frame.line + width:
                content += f"  {i}: {line}\n"

        return content

    def emit_calltrace_snippet(self, calltrace, n=5) -> str:
        content = "Below is the call trace that triggered the vulnerability:\n"
        for i, frame in enumerate(calltrace.frames[calltrace.sanitizer_index:]):
            content += self._emit_calltrace_frame_snippet(frame) + "\n"
            if i == n:
                break
        return content

    def create_prompt_context(self) -> str:
        prompt = ""

        bic_diff = self._bug.get_bic_diff()
        if bic_diff is None:
            prompt += self._emit_simple_vulnerability_info_snippet(self._bug)
        else:
            prompt += self._emit_full_bic_snippet(self._bug.cwes[0].name, bic_diff)

        cr = self._bug.challenge.get_crash_report()
        if cr is not None and len(cr.stacks) > 0:
            prompt += "\n\n"
            prompt += self.emit_calltrace_snippet(cr.stacks[0])

        return prompt

    @override
    def generate_prompt(self) -> Tuple[Prompt, Template]:
        prompt = Prompt()
        template = Template()

        prompt.header += self.create_prompt_context()

        return prompt, template

    def generate_trial(
            self,
            prompt: Prompt,
            template: Template,
            temperature: float
        ) -> Optional[PatchTrial]:

        dialog, patch_diff = self.run_agent(prompt.to_string(), temperature)

        if patch_diff == "":
            logger.info("No patch diff generated by the agent")
            return None

        return PatchTrial(
            bug=self._bug,
            dialog=dialog,
            prompt=deepcopy(prompt),
            template=deepcopy(template),
            diff=patch_diff,
            meta=PatchMeta(self._model.name(), temperature),
            op="generate")

    def generate_trials(
            self,
            prompt: Prompt,
            template: Template,
            temperature: float,
            n: int
        ) -> List[PatchTrial]:
        trials = []
        for _ in range(n):
            try:
                trial = self.generate_trial(prompt, template, temperature)
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.warning(f"Error while generating a trial: {e}")
                continue
            if trial is not None:
                trials.append(trial)
        return trials

    @override
    def generate(self) -> List[PatchTrial]:
        prompt, template = self.generate_prompt()

        results = []
        results += self.generate_trials(prompt, template, 0.0, (self._num_samples + 1) // 2)
        results += self.generate_trials(prompt, template, 0.3, self._num_samples // 2)

        return results

    def run_agent(self, prompt: str, temperature: float) -> Tuple[Dialog, str]:
        """
        Run the agent and return the dialog and the patch diff
        """
        agent = self.agent()(self._model, self._bug, temperature)
        if agent is None:
            raise AgentError(f"{self.name()} agent is not available")
        logger.info(f"{self.name()} agent is running with prompt: {prompt}")
        agent.query(prompt)
        return agent.get_dialogs(), agent.get_patch_diff()

    def evolve_prompt(self, trial: PatchTrial, outcome: PatchOutcome) -> Tuple[Prompt, Template]:
        prompt = Prompt()
        template = Template()
        prompt.header += "### Context:\n"
        prompt.header += PROMPT_EVOLVE

        prompt.header += "### Patch Diff:\n"
        prompt.header += f"```diff\n{trial.diff}\n```\n\n"
        prompt.header += "### Build Error Message:\n"
        prompt.header += f"```\n{outcome.message}\n```\n\n"
        return prompt, template

    @override
    def evolve(self, trial: PatchTrial, outcome: PatchOutcome) -> Optional[PatchTrial]:
        new_prompt, new_template = self.evolve_prompt(trial, outcome)

        new_dialog, new_patch_diff = self.run_agent(new_prompt.to_string(), 0.0)

        if new_patch_diff == "":
            logger.info("No patch diff generated by the agent")
            return None

        new_trial = PatchTrial(
            bug=self._bug,
            dialog=new_dialog,
            prompt=new_prompt,
            template=new_template,
            diff=new_patch_diff,
            meta=PatchMeta(self._model.name(), 0.0),
            op="evolve",
            parent=trial)
        return new_trial

    @staticmethod
    @abstractmethod
    def agent() -> Callable:
        pass

class Aider(AgentGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "aider"

    @override
    @staticmethod
    def agent() -> Callable:
        return AiderAgent

class AiderWhole(AgentGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "aider-whole"

    @override
    @staticmethod
    def agent() -> Callable:
        return lambda m, b, t: \
        AiderAgent(model=m, bug=b, temperature=t, edit_format=None, edit_single=True)

    @override
    def _emit_simple_vulnerability_info_snippet(self, bug: Bug) -> str:
        cwe = bug.cwes[0]
        func = find_function(bug.locations[0], None) # TODO: No build_info is okay?

        assert func.name is not None
        return (
            f"Fix the '{cwe.name}' vulnerability in `{func.name}` function. "
            f"Rewrite the function `{func.name}` in the file `{bug.src}`."
        )

    @override
    def _emit_full_bic_snippet(self, bug_class: str, bic_diff: str) -> str:
        cwe = self._bug.cwes[0]
        func = find_function(self._bug.locations[0], None)
        return (
            f"Fix the {func.name} function in {self._bug.src} "
            f"to address the '{cwe.name}' vulnerability introduced after the following commit:"
            f"\n\n```\n{bic_diff}\n```\n"
        )

class AiderRevert(AgentGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "aider-revert"

    @override
    def _emit_full_bic_snippet(self, bug_class: str, bic_diff: str) -> str:
        return (
            f"You will be given a diff of a commit that introduces a '{bug_class}' vulnerability. "
            f"Fix the given vulnerability by reverting parts of the given commit. "
            f"Here is the diff of the commit:"
            f"\n\n```\n{bic_diff}\n```\n"
        )

    @override
    def create_prompt_context(self) -> str:
        prompt = ""

        bic_diff = self._bug.get_bic_diff()
        if bic_diff is None:
            raise AgentError("BIC diff is required for AiderRevert")

        prompt += self._emit_full_bic_snippet(self._bug.cwes[0].name, bic_diff)

        return prompt

    @override
    @staticmethod
    def agent() -> Callable:
        return AiderAgent

class SWEGenerator(AgentGenerator):
    @override
    @staticmethod
    def name() -> str:
        return "swe-agent"

    @override
    @staticmethod
    def agent() -> Callable:
        return SWEAgent

AVAILBLE_GENERATORS =  [
#     DefaultPromptGenerator,
#     SingleFunctionPromptGenerator,
#     ZeroShotPromptGenerator,
#     ZeroShotNoTokenPromptGenerator,
#     GooglePromptGenerator,
    Aider,
    AiderWhole,
    AiderRevert,
    SWEGenerator,
]

def get_available_prompt_generators() -> List[str]:
    return [generator.name() for generator in AVAILBLE_GENERATORS]

def get_prompt_generator(name: str) -> Type[Generator]:
    for generator in AVAILBLE_GENERATORS:
        if generator.name() == name.lower():
            return generator

    raise ValueError(f'invalid prompt generator: {name}')
