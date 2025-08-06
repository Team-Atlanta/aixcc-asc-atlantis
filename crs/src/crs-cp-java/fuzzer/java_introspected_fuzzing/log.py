import logging

logger = None


def setup_logger(logfile):
    global logger

    # Create a custom logger
    logger = logging.getLogger(__name__)

    # Create handlers
    #c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(logfile)
    #c_handler.setLevel(logging.WARNING)
    f_handler.setLevel(logging.ERROR)

    # Create formatters and add it to handlers
    #c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    f_format = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    #logger.addHandler(c_handler)
    logger.addHandler(f_handler)


def warn(msg):
    global logger

    if logger is None:
        print(msg)
    else:
        logger.error(msg)


def error(msg):
    global logger

    if logger is None:
        print(msg)
    else:
        logger.error(msg)


def info(msg):
    global logger

    if logger is None:
        print(msg)
    else:
        logger.error(msg)


def debug(msg):
    global logger

    if logger is None:
        print(msg)
    else:
        logger.error(msg)
