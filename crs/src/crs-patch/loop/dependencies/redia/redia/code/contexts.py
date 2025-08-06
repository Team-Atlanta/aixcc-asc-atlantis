from logging import Logger
from pathlib import Path

from redia.summary.contexts import SummaryContext


class CodingContext(SummaryContext):
    working_directory: Path
    source_directory: Path
    logger: Logger
