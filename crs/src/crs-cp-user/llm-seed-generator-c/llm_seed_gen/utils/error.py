def fatal(message, logger=None):
    print(f'[Error][FATAL] {message}')
    print(f'[Error] Exiting program.')

    if logger is not None:
        logger.error(message)
        logger.error(f'[Error] Exiting program.')

    exit(1)


def print_error(message, logger=None):
    print(f'[Error] {message}')

    if logger is not None:
        logger.error(message)


def print_exception(e, stack_trace, logger=None):
    print_error(f'[Exception] {e}', logger)
    print_error(stack_trace, logger)
