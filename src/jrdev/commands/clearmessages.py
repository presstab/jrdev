#!/usr/bin/env python3

"""
ClearMessages command implementation for the JrDev terminal.
"""

from typing import Any, List

from jrdev.ui import terminal_print, PrintType


async def handle_clearmessages(terminal: Any, args: List[str]) -> None:
    """
    Handle the /clearmessages command to clear conversation history for all models.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal.clear_messages()
    terminal_print(f"Cleared message history", print_type=PrintType.SUCCESS)
