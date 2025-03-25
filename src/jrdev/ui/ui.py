#!/usr/bin/env python3

"""
UI utilities for JrDev terminal interface.
"""

import logging
import platform
import threading
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# Initialize colorama for Windows terminal color support
if platform.system() == 'Windows':
    try:
        import colorama
        colorama.init()
    except ImportError:
        # If colorama isn't installed, colors may not work correctly on Windows
        pass

# Get the global logger instance
logger = logging.getLogger("jrdev")


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
    SUBHEADER = auto()   # Category headers


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
    PrintType.COMMAND: COLORS["BRIGHT_BLUE"] + COLORS["BOLD"],
    PrintType.HEADER: (COLORS["BRIGHT_WHITE"] + COLORS["BOLD"] +
                        COLORS["UNDERLINE"]),
    PrintType.SUBHEADER: COLORS["BRIGHT_WHITE"] + COLORS["BOLD"],
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
    If the execution is not in the main thread, log the message instead.

    Args:
        message: The message to print
        print_type: The type of message (determines formatting)
        end: The end character (default: newline)
        prefix: Optional prefix to add before the message
        flush: Whether to flush the output (useful for streaming outputs)
    """
    # Check if we're in the main thread
    if threading.current_thread() is not threading.main_thread():
        # Not in main thread, log the message instead
        logger = logging.getLogger("jrdev")

        # Determine log level based on print_type
        if print_type == PrintType.ERROR:
            logger.error(message)
        elif print_type == PrintType.WARNING:
            logger.warning(message)
        elif print_type == PrintType.SUCCESS:
            logger.info(f"SUCCESS: {message}")
        else:
            logger.info(message)
        return
    # In main thread, print to terminal as usual
    format_code = FORMAT_MAP.get(print_type, COLORS["RESET"])
    formatted_prefix = f"{format_code}{prefix} " if prefix else format_code

    print(f"{formatted_prefix}{message}{COLORS['RESET']}",
          end=end, flush=flush)


def display_diff(diff_lines: List[str]) -> None:
    """
    Display a unified diff to the terminal with color-coded additions and deletions.

    Args:
        diff_lines: List of lines from a unified diff
    """
    if not diff_lines:
        terminal_print("No changes detected in file content.", PrintType.WARNING)
        return

    terminal_print("File changes diff:", PrintType.HEADER)
    for line in diff_lines:
        if line.startswith('+'):
            terminal_print(line.rstrip(), PrintType.SUCCESS)
        elif line.startswith('-'):
            terminal_print(line.rstrip(), PrintType.ERROR)
        else:
            terminal_print(line.rstrip())


def prompt_for_confirmation(prompt_text: str = "Apply these changes?") -> Tuple[str, Optional[str]]:
    """
    Prompt the user for confirmation with options to apply, reject, request changes,
    or edit the changes in a text editor.

    Args:
        prompt_text: The text to display when prompting the user

    Returns:
        Tuple of (response, message):
            - response: 'yes', 'no', 'request_change', or 'edit'
            - message: User's feedback message when requesting changes,
                      or edited content when editing, None otherwise
    """
    while True:
        response = input(f"\n{prompt_text} ✅ Yes [y] | ❌ No [n] | 🔄 Request Change [r] | ✏️  Edit [e]: ").lower().strip()
        if response in ('y', 'yes'):
            return 'yes', None
        elif response in ('n', 'no'):
            return 'no', None
        elif response in ('r', 'request', 'request_change'):
            terminal_print("Please enter your requested changes:", PrintType.INFO)
            message = input("> ")
            return 'request_change', message
        elif response in ('e', 'edit'):
            terminal_print("Opening editor... (Ctrl+S/Alt+W to save, Ctrl+Q/Alt+Q/ESC to quit)", PrintType.INFO)
            return 'edit', None
        else:
            terminal_print("Please enter 'y', 'n', 'r', or 'e'", PrintType.ERROR)
