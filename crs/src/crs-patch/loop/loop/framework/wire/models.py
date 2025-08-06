from dataclasses import dataclass
from typing import Iterator

from loop.commons.context.models import RequiresContext
from loop.commons.logging.context_manager import logging_performance
from loop.framework.action.models import Action
from loop.framework.action.variants import (
    DiffAction,
    RuntimeErrorAction,
    WrongFormatAction,
)
from loop.framework.agent.protocols import AgentProtocol
from loop.framework.challenge_project.models import ChallengeSource
from loop.framework.detection.models import Detection
from loop.framework.effect.models import Effect
from loop.framework.effect.variants import (
    SoundEffect,
    UnknownErrorEffect,
    WrongFormatEffect,
)
from loop.framework.environment.protocols import EnvironmentProtocol
from loop.framework.evaluator.protocols import EvaluatorProtocol
from loop.framework.picker.protocols import PickerProtocol
from loop.framework.seed.models import Seed
from loop.framework.seed.variants import ErrorSeed, InitialSeed
from loop.framework.wire.context import WireContext


@dataclass
class Wire:
    id: str
    max_iteration: int
    environment: EnvironmentProtocol
    picker: PickerProtocol
    agent: AgentProtocol
    evaluator: EvaluatorProtocol

    def run(
        self, detection: Detection, challenge_source: ChallengeSource
    ) -> RequiresContext[Iterator[tuple[Action, Effect]], WireContext]:
        def _(mutable_context: WireContext) -> Iterator[tuple[Action, Effect]]:
            mutable_seed: Seed = InitialSeed()

            while len(mutable_context["history"]) < self.max_iteration:

                try:
                    with logging_performance(
                        mutable_context["logger"],
                        f"{mutable_context['log_prefix']}:wire:run_once:{self.max_iteration - len(mutable_context['history'])}",
                    ):
                        action, effect, mutable_seed = self.run_once(
                            mutable_seed,
                            detection=detection,
                            challenge_source=challenge_source,
                        )(mutable_context)

                except Exception as e:
                    mutable_context["logger"].error(e, exc_info=True)
                    action = RuntimeErrorAction(e)
                    effect = UnknownErrorEffect(e)

                mutable_context["history"].append((mutable_seed, action, effect))

                yield action, effect

                match action, effect:
                    case (RuntimeErrorAction(), _):
                        break
                    case (_, UnknownErrorEffect()):
                        break
                    case (_, _):
                        pass

        return RequiresContext(_)

    def run_once(
        self, seed: Seed, detection: Detection, challenge_source: ChallengeSource
    ) -> RequiresContext[tuple[Action, Effect, Seed], WireContext]:
        def _(context: WireContext):
            self.environment.restore(challenge_source).unwrap()

            with logging_performance(
                context["logger"],
                f"{context['log_prefix']}:wire:act",
            ):
                action = self.agent.act(detection, challenge_source, seed)(context)

            match action:
                case WrongFormatAction(error):
                    effect = WrongFormatEffect(error)
                    next_seed = ErrorSeed(message=str(error))
                case DiffAction():
                    with logging_performance(
                        context["logger"],
                        f"{context['log_prefix']}:wire:evaluate",
                    ):
                        effect = self.evaluator.evaluate(
                            detection=detection,
                            challenge_source=challenge_source,
                            action=action,
                            environment=self.environment,
                        )(context)

                    with logging_performance(
                        context["logger"],
                        f"{context['log_prefix']}:wire:pick",
                    ):
                        next_seed = self.picker.pick(action, effect)(context)
                case RuntimeErrorAction(error):
                    effect = UnknownErrorEffect(error)
                    next_seed = InitialSeed()

            match effect:
                case SoundEffect():
                    self.agent.on_sound_effect()
                case _:
                    self.agent.on_not_sound_effect()

            match action:
                case DiffAction():
                    context["logger"].info(action.content)
                case WrongFormatAction():
                    context["logger"].error(action.error)
                case RuntimeErrorAction():
                    context["logger"].error(action.error)

            return action, effect, next_seed

        return RequiresContext(_)
