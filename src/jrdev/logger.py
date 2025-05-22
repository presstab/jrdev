#!/usr/bin/env python3
"""
Logging module for JrDev application.
"""

import logging
import os
from datetime import datetime
from typing import Optional


def setup_logger(log_dir: Optional[str] = None) -> logging.Logger:
    """
    Setup and configure the application logger.

    Args:
        log_dir: Optional directory to store log file. Defaults to current working directory.

    Returns:
        Configured logger instance
    """
    # Use current working directory if log_dir not specified
    if log_dir is None:
        log_dir = os.getcwd()

    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Configure log file path
    log_path = os.path.join(log_dir, "jrdev.log")

    # Create logger
    logger = logging.getLogger("jrdev")
    logger.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)

    # Create formatter and add to handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    # Log application start
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"-----------JrDev application started at {timestamp}-----------")

    return logger
