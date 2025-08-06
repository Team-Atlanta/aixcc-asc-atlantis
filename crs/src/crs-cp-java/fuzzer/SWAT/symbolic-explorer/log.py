import json
import logging
import os

def setup_logger(name, log_file, level=logging.INFO, useConsoleHandler=True):
    #formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    formatter = logging.Formatter("[%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

    fileHandler = logging.FileHandler(log_file)
    fileHandler.setFormatter(formatter)
    logger = logging.getLogger(name)
    if useConsoleHandler:
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)
    logger.setLevel(level)
    logger.addHandler(fileHandler)

    return logger

class Logger(object):
    def __init__(self):
        pass

    def init_logger(self, log_path):
        self.log_directory = log_path[0]
        print(f'Initializing logging at: {self.log_directory}')
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        self.logger = setup_logger("main_logger", f'{self.log_directory}/explorer.log')
        self.solution_logger = setup_logger("solution_logger", f'{self.log_directory}/solutions.log')
        self.args_logger = setup_logger("args_logger", f'{self.log_directory}/args.log')
        self.constraints_logger = setup_logger("constraints_logger", f'{self.log_directory}/constraints.log')

logger = Logger()
"""
log_directory = './logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)  # Create the logs directory if it does not exist

logger = setup_logger("main_logger", f'{log_directory}/explorer.log')
logger.info("Logger has been set up.")

solution_logger = setup_logger("solution_logger", f'{log_directory}/solutions.log')
args_logger = setup_logger("args_logger", f'{log_directory}/args.log')
constraints_logger = setup_logger("constraints_logger", f'{log_directory}/constraints.log')
"""

class GeneratedInputLogger(object):
    def __init__(self):
        self.inputs = []

    def add_input(self, _input):
        self.inputs.append(_input)

    def get_logged_inputs(self):
        return list(self.inputs)

    def write_to_file(self, filename):
        with open(filename, "wt") as f:
            f.write(json.dumps(self.inputs))
