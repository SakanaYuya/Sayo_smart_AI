# backend/utils/logging_config.py

import datetime

def get_timestamp():
    """Returns the current time in [HH:MM:SS] format."""
    return datetime.datetime.now().strftime("[%H:%M:%S]")

def log_message(message):
    """Prints a message with a timestamp."""
    print(f"{get_timestamp()} {message}")
