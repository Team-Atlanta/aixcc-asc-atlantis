import logging


class KasanReport:
    def __init__(self, kasan_log: str, timed_out: bool):
        self.kasan_log = kasan_log
        self.timed_out = timed_out

    def __str__(self):
        return self.kasan_log

    def is_crash(self, sanitizers: list[str]) -> bool:
        logger = logging.getLogger(__name__)
        for sanitizer_string in sanitizers:
            if sanitizer_string in self.kasan_log:
                logger.info(f"Found sanitizer string: {sanitizer_string}")
                return True
        return False


def kasan_parse(kasan_log: str, timed_out: bool) -> KasanReport:
    return KasanReport(kasan_log, timed_out)
