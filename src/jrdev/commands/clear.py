#!/usr/bin/env python3

"""
Clear command implementation for the JrDev application.
"""

from typing import Any, List

from jrdev.ui.ui import terminal_print, PrintType


async def handle_clear(app: Any, args: List[str]):
    """
    Handle the /clear command to clear conversation history.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    app.clear_messages()
    terminal_print("Conversation history cleared.", print_type=PrintType.SUCCESS)
