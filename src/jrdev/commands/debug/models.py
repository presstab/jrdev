#!/usr/bin/env python3

"""
Debug command to test the non-curses model selection UI.
This is a temporary command for testing purposes.
"""
from typing import Any, List

from jrdev.commands.models import handle_models


async def handle_modelswin(app: Any, args: List[str]) -> None:
    """
    Force the non-curses model selection UI.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    # Pass --no-curses flag to force non-curses UI
    await handle_models(app, ["modelswin", "--no-curses"])
