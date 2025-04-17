import logging
import sys
import os
from datetime import datetime
from src.framework import config
from src.utility.constants import LOG_FORMAT

current_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    record = current_factory(*args, **kwargs)
    record.clusterctx = (
        f"- C[{config.current_cluster_name()}]" if config.nclusters > 1 else ""
    )
    return record


def set_log_record_factory():
    logging.setLogRecordFactory(record_factory)


def setup_logging(log_cli_level="INFO", log_file_path=None):
    """
    Set up global logging configuration for console and optional file
    """
    set_log_record_factory()
    level = logging.getLevelName(log_cli_level.upper())
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT)

    # Console handler
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file_path:
        # Make sure directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
