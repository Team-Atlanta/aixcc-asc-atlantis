from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Generator

from . import one, two
from .lib import SSyscall, TestLang, TTokens, parse_test_lang


class HarnessType(Enum):
    TYPE1 = 1
    TYPE2 = 2


def identify_harness_type(syntax_parsed: TestLang) -> HarnessType | None:
    if TTokens.INPUT not in syntax_parsed.records:
        return None

    input_record = syntax_parsed.records[TTokens.INPUT]
    if "COMMAND_CNT" not in map(lambda x: x.name, input_record.fields):
        return HarnessType.TYPE1
    else:
        return HarnessType.TYPE2


def reproduce_blob(poc_trace: list[SSyscall], harness: Path, syntax: Path) -> Generator[bytes, None, None]:
    logger = getLogger(__name__)

    syntax_parsed = None
    with open(syntax) as syntax_file:
        syntax_parsed = parse_test_lang(syntax_file.read())

    if syntax_parsed is None:
        logger.warn("TestLang file %s parse failed for %s. Ignoring...", syntax, harness)
        return

    harness_type = identify_harness_type(syntax_parsed)

    if harness_type is None:
        logger.warn("TestLang file %s has no %s field. Ignoring...", syntax, TTokens.INPUT)
        return
    elif harness_type == HarnessType.TYPE1:
        yield from one.reproduce_blob(poc_trace, harness, syntax_parsed)
    elif harness_type == HarnessType.TYPE2:
        yield from two.reproduce_blob(poc_trace, harness, syntax_parsed)
    else:
        raise Exception("Unreachable.")
