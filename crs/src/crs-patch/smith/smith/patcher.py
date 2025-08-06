import logging
import traceback

from typing import List, Tuple
from pathlib import Path

from .challenge import Challenge
from .bug import Bug
from .generator import Generator
from .patch_trial import PatchOutcome, PatchTrial, PatchResult
from .runner import TestResult

l = logging.getLogger(__name__)

class Patcher():
    def __init__(self,
                challenge: Challenge,
                bug: Bug,
                generators: List[Generator],
                num_evolves: int = 0):
        self._challenge = challenge
        self._bug = bug
        self._generators = generators
        self._num_evolves = num_evolves
        self._candidates: List[PatchTrial] = []
        self._results: List[Tuple[PatchOutcome, PatchTrial]] = []

    def _create_candidates(self, generator: Generator) -> None:
        self._candidates += generator.generate()

    def _validate_candidates(self, generator: Generator) -> None:
        for candidate in self._candidates:
            outcome = self._try_patch(candidate)
            self._results.append((outcome, candidate))

            if self._can_evolve(candidate, outcome):
                new_trial = generator.evolve(candidate, outcome)
                if new_trial is not None:
                    self._candidates.append(new_trial)

        self._candidates = []

    def run_all(self):
        while True:
            try:
                for generator in self._generators:
                    self._create_candidates(generator)
                    self._validate_candidates(generator)
            except Exception as e: # pylint: disable=broad-except
                l.warning(f"Error while running generators: {e}")
                traceback.print_exc()

            if not self._bug.switch_to_next_candidate():
                l.info("No more fault candidates")
                break

        return self._results

    def _can_evolve(self, trial: PatchTrial, outcome: PatchOutcome) -> bool:
        if self._num_evolves == 0:
            # No evolution
            return False

        if trial.round >= self._num_evolves:
            return False

        # We evolve only when compile error occurs
        return outcome.is_compile_error()

    def _get_outcome(self, trial: PatchTrial, output_dir: Path) -> PatchOutcome:
        args = trial.to_build_args(self._challenge, output_dir)

        (_ok, _msg) = self._challenge.git_reset(output_dir)
        # TODO: Check whether the reset is successful

        (ok, msg) = self._challenge.perform_build(output_dir, args=args)
        if ok != TestResult.OK:
            # l.debug(f"  - {msg}")
            return PatchOutcome(trial.name, PatchResult.COMPILE_ERROR, msg)
        l.debug("  - Build OK")

        (ok, msg) = self._challenge.perform_functional_test(output_dir)
        if ok != TestResult.OK:
            l.debug(f"  - {msg}")
            return PatchOutcome(trial.name, PatchResult.FUNCTIONAL_ERROR, msg)
        l.debug("  - Functional test OK")

        (ok, msg) = self._challenge.perform_security_test(output_dir)
        if ok != TestResult.OK:
            l.debug(f"  - {msg}")
            return PatchOutcome(trial.name, PatchResult.SECURITY_ERROR, msg)

        l.debug("  - Security test OK")
        return PatchOutcome(trial.name, PatchResult.SUCCESS, msg)

    def _try_patch(self, trial: PatchTrial) -> PatchOutcome:
        output_dir = self._bug.get_output_dir() / trial.name
        output_dir.mkdir(parents=True, exist_ok=True)

        outcome = self._get_outcome(trial, output_dir)
        if outcome.is_success():
            trial.write_to_file(output_dir, success=True)
        else:
            trial.write_to_file(output_dir)
        return outcome
