import datetime
import os
import logging

from llm_seed_gen.utils import error


class LoggerManager:
    _instance = None

    def __new__(cls, log_dir):
        if not cls._instance:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir):
        if self._initialized:
            return

        self.pid = os.getpid()
        self.start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        self.log_dir = log_dir
        self._create_directory_if_does_not_exists(log_dir)

        if not os.path.isdir(log_dir):
            error.fatal(f'Unable to create log_dir {log_dir}')

        self._initialized = True

    def _create_directory_if_does_not_exists(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except:
            return

    def get_logger(self, name, loglevel=logging.INFO):
        logger = logging.getLogger(name)
        logger.setLevel(loglevel)

        if not logger.handlers:
            handler = logging.FileHandler(f'{self.log_dir}/{name}_{self.pid}_{self.start_time}.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger
