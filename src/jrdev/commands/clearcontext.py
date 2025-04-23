#!/usr/bin/env python3

"""
ClearContext command implementation for the JrDev terminal.
"""

from typing import Any, List
from jrdev.ui.ui import PrintType


async def handle_clearcontext(app: Any, args: List[str], worker_id: str) -> None:
    """
    Handle the /clearcontext command to clear context files and conversation history.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    # Clear the context array
    msg_thread = app.get_current_thread()
    num_files = len(msg_thread.context)
    msg_thread.context.clear()
    app.ui.chat_thread_update(msg_thread.thread_id)
    app.ui.print_text(f"Cleared {num_files} file(s) from context.", print_type=PrintType.SUCCESS)
    app.ui.print_text(f"Note that this doesn't remove context that has already been sent in a message thread's history. In order to start with fresh context, start a new thread.", print_type=PrintType.SUCCESS)
