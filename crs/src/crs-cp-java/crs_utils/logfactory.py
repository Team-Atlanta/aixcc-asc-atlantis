import logging
import os

from .settings import DEV

# coloredlogs.install(fmt='%(asctime)s %(levelname)s %(message)s')

class LogFactory:
    #TODO: Integrate with pool logging
    def __init__(self, name = "crs.log"):
        self.log_file = name
        self.setup()
    def setup(self):
        if DEV:
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
        except Exception as e:
            print(f"Failed to remove log file: {e}")
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG) 
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                file_handler,
                console_handler,
            ]
        )

LOG = logging.getLogger()

def get_level(logger):
    return logger.getEffectiveLevel()

def logging_init(workdir):
    global LOG
    logs_dir = workdir / "logs"
    os.makedirs(logs_dir, exist_ok = True)
    _log_factory = LogFactory(name = logs_dir / "crs.log")
    LOG = logging.getLogger("crs")
