# backend/utils/logging_config.py

import datetime
import config

def get_timestamp():
    """Returns the current time in [HH:MM:SS] format."""
    return datetime.datetime.now().strftime("[%H:%M:%S]")

def log_message(message):
    """Prints a message with a timestamp, only if IS_MAKER_MODE is True."""
    if config.IS_MAKER_MODE:
        print(f"{get_timestamp()} {message}")

def print_separator():
    """Prints a separator line, only if IS_MAKER_MODE is True."""
    if config.IS_MAKER_MODE:
        print("######")
