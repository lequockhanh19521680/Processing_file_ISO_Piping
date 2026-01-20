"""
Logging utility module for PDF Search Tool.

This module configures and provides centralized logging functionality with both
file and console handlers. File logging includes full DEBUG level details, while
console logging is minimal to keep the Rich UI clean.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from ..config import (
    LOG_FILE,
    LOG_LEVEL_FILE,
    LOG_LEVEL_CONSOLE,
    LOG_FORMAT,
    LOG_DATE_FORMAT
)


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Configure and return a logger instance with file and console handlers.
    
    File Handler:
        - Logs everything at DEBUG level
        - Includes timestamps, thread names, full stack traces
        - Saved to logs/system.log
    
    Console Handler:
        - Only logs ERROR level and above
        - Keeps terminal clean for Rich UI
    
    Args:
        name: Name for the logger. If None, returns root logger.
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    
    # File handler - DEBUG level, detailed logging
    file_handler = logging.FileHandler(
        LOG_FILE,
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL_FILE))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler - ERROR level only, minimal output
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, LOG_LEVEL_CONSOLE))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    If the logger hasn't been configured yet, it will be set up automatically.
    
    Args:
        name: Name for the logger (typically __name__ of the calling module)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # If no handlers, set up the logger
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


# Initialize the root logger when module is imported
_root_logger = setup_logger()
