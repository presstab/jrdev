#!/usr/bin/env python3

"""
Project context command implementation for the JrDev terminal.
"""

from jrdev.ui.ui import terminal_print, PrintType


async def handle_projectcontext(terminal, args):
    """
    Handle the /projectcontext command to toggle using project context in requests.
    
    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments, expecting ['projectcontext', '<on/off>']
    """
    if len(args) < 2:
        terminal_print("Usage: /projectcontext <on/off>", PrintType.ERROR)
        return

    setting = args[1].lower()
    
    if setting == "on":
        terminal.use_project_context = True
        terminal_print("Project context is now ON", PrintType.SUCCESS)
    elif setting == "off":
        terminal.use_project_context = False
        terminal_print("Project context is now OFF", PrintType.SUCCESS)
    else:
        terminal_print("Usage: /projectcontext <on/off>", PrintType.ERROR)