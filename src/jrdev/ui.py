#!/usr/bin/env python3

"""
UI utilities for JrDev terminal interface.
"""

from enum import Enum, auto
from typing import Any, Dict, Optional


class PrintType(Enum):
    """Types of terminal output with different formatting."""
    INFO = auto()        # General information
    ERROR = auto()       # Error messages
    PROCESSING = auto()  # Processing/loading indicators
    LLM = auto()         # AI model responses
    USER = auto()        # User input echoing
    SUCCESS = auto()     # Success messages
    WARNING = auto()     # Warning messages
    COMMAND = auto()     # Command output
    HEADER = auto()      # Headers/titles


# ANSI color codes
COLORS: Dict[str, str] = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "ITALIC": "\033[3m",
    "UNDERLINE": "\033[4m",
    "BLACK": "\033[30m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "BRIGHT_BLACK": "\033[90m",
    "BRIGHT_RED": "\033[91m",
    "BRIGHT_GREEN": "\033[92m",
    "BRIGHT_YELLOW": "\033[93m",
    "BRIGHT_BLUE": "\033[94m",
    "BRIGHT_MAGENTA": "\033[95m",
    "BRIGHT_CYAN": "\033[96m",
    "BRIGHT_WHITE": "\033[97m",
}


# Mapping print types to their formatting
FORMAT_MAP: Dict[PrintType, str] = {
    PrintType.INFO: COLORS["BRIGHT_WHITE"],
    PrintType.ERROR: COLORS["BRIGHT_RED"],
    PrintType.PROCESSING: COLORS["BRIGHT_CYAN"] + COLORS["DIM"],
    PrintType.LLM: COLORS["BRIGHT_GREEN"],
    PrintType.USER: COLORS["BRIGHT_YELLOW"],
    PrintType.SUCCESS: COLORS["BRIGHT_GREEN"] + COLORS["BOLD"],
    PrintType.WARNING: COLORS["BRIGHT_YELLOW"] + COLORS["BOLD"],
    PrintType.COMMAND: COLORS["BRIGHT_BLUE"],
    PrintType.HEADER: COLORS["BRIGHT_WHITE"] + COLORS["BOLD"] + COLORS["UNDERLINE"],
}


def terminal_print(
    message: Any,
    print_type: PrintType = PrintType.INFO,
    end: str = "\n",
    prefix: Optional[str] = None,
    flush: bool = False
) -> None:
    """
    Print formatted text to the terminal with color coding based on the message type.

    Args:
        message: The message to print
        print_type: The type of message (determines formatting)
        end: The end character (default: newline)
        prefix: Optional prefix to add before the message
        flush: Whether to flush the output (useful for streaming outputs)
    """
    format_code = FORMAT_MAP.get(print_type, COLORS["RESET"])
    formatted_prefix = f"{format_code}{prefix} " if prefix else format_code

    print(f"{formatted_prefix}{message}{COLORS['RESET']}", end=end, flush=flush)
