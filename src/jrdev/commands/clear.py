#!/usr/bin/env python3

"""
Clear command implementation for the JrDev terminal.
"""

from jrdev.ui import terminal_print, PrintType


async def handle_clear(terminal, args):
    """
    Handle the /clear command to clear conversation history.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal.clear_messages()
    terminal_print("Conversation history cleared.", print_type=PrintType.SUCCESS)
