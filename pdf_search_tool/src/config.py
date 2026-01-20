"""
Configuration module for PDF Search Tool.

This module contains all configuration constants, path settings, and default values
used throughout the application.
"""

import os
from pathlib import Path

# Version information
VERSION = "2.0.0"
APP_NAME = "PDF Keyword Search Tool"

# Performance settings
DEFAULT_MAX_WORKERS = 50  # Number of concurrent threads for PDF processing

# Directory paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Logging configuration
LOG_FILE = LOGS_DIR / "system.log"
LOG_LEVEL_FILE = "DEBUG"  # File logging level
LOG_LEVEL_CONSOLE = "ERROR"  # Console logging level (errors only)
LOG_FORMAT = "%(asctime)s - [%(threadName)s] - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Excel column names
KEYWORD_COLUMN_NAMES = ['ma_ho', 'mã hố', 'ma ho', 'keyword', 'keywords']

# Result column headers
RESULT_COLUMNS = {
    'ma_ho': 'ma_ho',
    'found': 'found',
    'file_name': 'file_name',
    'file_path': 'file_path',
    'match_type': 'Match_Type'  # Changed from match_count and status
}

# Search settings
PDF_EXTENSIONS = ['.pdf', '.PDF']
CASE_SENSITIVE_SEARCH = False

# UI Settings
PROGRESS_BAR_NCOLS = 100
STATUS_UPDATE_INTERVAL = 0.1  # seconds
MAX_KEYWORD_DISPLAY_LENGTH = 40  # Maximum characters to display for keywords in UI
MAX_LOCATION_PATH_LENGTH = 50  # Maximum characters to display for folder paths in UI
LOCATION_PATH_SUFFIX_LENGTH = 47  # Characters to show from end of path when truncated
