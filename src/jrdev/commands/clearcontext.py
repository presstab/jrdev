#!/usr/bin/env python3

"""
ClearContext command implementation for the JrDev terminal.
"""

from typing import Any, List
from jrdev.ui.ui import terminal_print, PrintType


async def handle_clearcontext(app: Any, args: List[str]) -> None:
    """
    Handle the /clearcontext command to clear context files and conversation history.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    # Clear the context array
    num_files = len(app.state.context)
    app.state.clear_context()
    terminal_print(f"Cleared {num_files} file(s) from context.", print_type=PrintType.SUCCESS)

    # Clear conversation history
    app.clear_messages()
