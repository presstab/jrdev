#!/usr/bin/env python3

"""
Exit command implementation for the JrDev application.
"""

from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_exit(app: Any, _args: List[str], _worker_id: str):
    """
    Safely terminates the JrDev application.

    This command signals the main application loop to stop, ensuring a clean shutdown.

    Usage:
      /exit
    """
    app.logger.info("User requested exit via /exit command")
    app.ui.print_text("Exiting JrDev terminal...", print_type=PrintType.INFO)

    # Set the running flag to False to signal the main loop to exit
    app.state.running = False

    # Send the exit signal to the UI layer
    await app.ui.signal_exit()

    # Make sure the state update is visible
    app.logger.info(f"Running state set to: {app.state.running}")

    # Return a special code that indicates we want to exit
    return "EXIT"
