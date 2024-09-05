import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import TypeVar

from app.core.config_manager import config

T = TypeVar('T')


def setup_logger(name: str,
                 add_stdout: bool = True,
                 log_level: int = logging.INFO) -> logging.Logger:
    """
    Sets up a logger

    Args:
        name (str): The name of the logger.
        add_stdout (bool): Whether to log to stdout.
        log_level (int): The logging level.
    Returns:
        logging.Logger: The logger instance.
    """
    log_level = log_level or config.log_level
    log_format = logging.Formatter(f'{config.env_name} - %(asctime)s - %(message)s')

    # Log to stdout and to file
    os.makedirs(os.path.dirname(config.log_file), exist_ok=True)
    stdout_handler = logging.StreamHandler(sys.stdout)
    file_handler = TimedRotatingFileHandler(config.log_file, when="midnight", interval=1)
    file_handler.suffix = "%Y%m%d"

    # Set the logger format
    stdout_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    # Configure logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    if add_stdout and config.log_stdout:
        logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)
    return logger
