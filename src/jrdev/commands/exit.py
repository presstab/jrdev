#!/usr/bin/env python3

"""
Exit command implementation for the JrDev application.
"""

from typing import Any, List
from jrdev.ui.ui import terminal_print, PrintType
import sys


async def handle_exit(app: Any, args: List[str]):
    """
    Handle the /exit command to terminate the application.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    app.logger.info("User requested exit via /exit command")
    terminal_print("Exiting JrDev terminal...", print_type=PrintType.INFO)
    
    # Set the running flag to False to signal the main loop to exit
    app.state.running = False
    
    # Make sure the state update is visible
    app.logger.info(f"Running state set to: {app.state.running}")
    
    # Return a special code that indicates we want to exit
    return "EXIT"
