import logging
import logging.handlers

from rich.logging import RichHandler


def use_logger(name: str | None = None, level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level="WARNING",
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    match name:
        case None:
            logger = logging.getLogger(__name__)
        case _:
            logger = logging.getLogger(name)

    logger.setLevel(level)

    return logger
