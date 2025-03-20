#!/usr/bin/env python3

"""
Process command implementation for the JrDev terminal.
Controls whether to process file requests and code changes in LLM responses.
"""

from typing import Any, List

from jrdev.ui.ui import terminal_print, PrintType


async def handle_process(terminal: Any, args: List[str]) -> None:
    """
    Handle the /process command to enable or disable processing of file requests
    and code changes in LLM responses.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (on/off)
    """
    if len(args) < 2:
        terminal_print("Usage: /process on|off", print_type=PrintType.ERROR)
        return
    
    setting = args[1].lower()
    
    if setting == "on":
        terminal.process_follow_up = True
        terminal_print("Processing of file requests and code changes is now enabled.", 
                       print_type=PrintType.SUCCESS)
        terminal_print("The LLM can now request and modify files.", 
                       print_type=PrintType.INFO)
    elif setting == "off":
        terminal.process_follow_up = False
        terminal_print("Processing of file requests and code changes is now disabled.", 
                       print_type=PrintType.SUCCESS)
        terminal_print("The LLM can no longer request or modify files.", 
                       print_type=PrintType.INFO)
    else:
        terminal_print("Invalid option. Use '/process on' or '/process off'.", 
                       print_type=PrintType.ERROR)