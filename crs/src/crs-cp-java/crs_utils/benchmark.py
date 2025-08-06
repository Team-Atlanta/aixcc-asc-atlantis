from pathlib import Path
# from .settings import DEV

class Benchmark:
    def __init__(self, base, harness_id, name, source, binary, sanitizer = None):
        self.id: str = harness_id
        self.name: str = name
        self.source: Path = base / source
        if binary == "n/a":
            self.binary: Path = None
        else:
            self.binary: Path = base / Path(binary)
        # if DEV:
        #     # We only know answer for dev
        #     self.sanitizer = sanitizer
