#!/usr/bin/env python3

"""
ClearContext command implementation for the JrDev terminal.
"""

from jrdev.ui.ui import terminal_print, PrintType


async def handle_clearcontext(terminal, args):
    """
    Handle the /clearcontext command to clear context files and conversation history.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    # Clear the context array
    num_files = len(terminal.context)
    terminal.context = []
    terminal_print(f"Cleared {num_files} file(s) from context.", print_type=PrintType.SUCCESS)

    # Clear conversation history
    terminal.clear_messages()
