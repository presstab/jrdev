#!/usr/bin/env python3

"""
ClearMessages command implementation for the JrDev terminal.
"""

from typing import Any, List

from jrdev.ui.ui import terminal_print, PrintType


async def handle_clearmessages(app: Any, args: List[str]) -> None:
    """
    Handle the /clearmessages command to clear conversation history for all models.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    app.clear_messages()
    terminal_print(f"Cleared message history", print_type=PrintType.SUCCESS)
