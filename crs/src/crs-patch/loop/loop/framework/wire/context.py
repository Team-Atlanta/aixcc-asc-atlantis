import logging
from typing import TypedDict

from loop.framework.action.models import Action
from loop.framework.effect.models import Effect
from loop.framework.seed.models import Seed


class WireContext(
    TypedDict,
):
    log_prefix: str
    history: list[tuple[Seed, Action, Effect]]
    logger: logging.Logger
