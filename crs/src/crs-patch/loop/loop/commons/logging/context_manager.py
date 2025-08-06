import time
from contextlib import contextmanager
from logging import Logger


@contextmanager
def logging_performance(logger: Logger, key: str):
    logger.info(f"[logging_performance]({key}) Started...")

    start = time.perf_counter()
    yield
    end = time.perf_counter()

    logger.info(f"[logging_performance]({key}) Took {end - start:.2f} seconds")
