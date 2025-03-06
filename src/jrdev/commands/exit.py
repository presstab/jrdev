#!/usr/bin/env python3

"""
Exit command implementation for the JrDev terminal.
"""

from jrdev.ui import terminal_print, PrintType


async def handle_exit(terminal, args):
    """
    Handle the /exit command to terminate the terminal.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal_print("Exiting JrDev terminal...", print_type=PrintType.INFO)
    terminal.running = False
    return True
