import traceback
from logging import getLogger
from pathlib import Path

import yaml

SANITIZERS = "sanitizers"
DEFAULT_SANITIZERS = list()


def get_sanitizer_list(proj_def_path: Path) -> list[str]:
    logger = getLogger(__name__)
    proj_def = None
    with open(proj_def_path, "r") as p_file:
        try:
            proj_def = yaml.safe_load(p_file)
        except Exception as e:
            logger.warning("Failed parsing project definition file. Using default sanitizer list...")
            logger.debug("Error trace:\n%s", "".join(traceback.format_exception(e)))
            return DEFAULT_SANITIZERS

    sanitizers: dict[str, str] = proj_def[SANITIZERS]
    return list(sanitizers.values())
