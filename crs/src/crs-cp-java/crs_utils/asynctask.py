
import logging
import os
from .settings import DEV
from .config import Config


class AsyncTask:
    def __init__(self):
        pass

    def logging_init(self, log_name="pool"):
        builddir = Config().builddir
        LOG = logging.getLogger(log_name)
        logs_dir = builddir / "logs"
        log_file = log_name + ".log"
        try:
            if os.path.exists(logs_dir / log_file):
                os.remove(logs_dir / log_file)
        except Exception as e:
            print(f"Failed to remove log file: {e}")
        file_handler = logging.FileHandler(logs_dir / log_file)
        format = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s - %(message)s")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(format)
        LOG.addHandler(file_handler)
        if DEV:
            LOG.setLevel(logging.DEBUG)
        else:
            LOG.setLevel(logging.INFO)
        return LOG
    
    async def run(self):
        pass