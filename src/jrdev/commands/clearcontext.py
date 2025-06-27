#!/usr/bin/env python3

"""
ClearContext command implementation for the JrDev terminal.
"""

from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_clearcontext(app: Any, _args: List[str], _worker_id: str) -> None:
    """
    Clears all files from the current thread's context window.

    This removes all files that were added with `/addcontext`. It does not erase
    the conversation history, but it prevents the cleared files from being
    included in future prompts in this thread.

    Usage:
      /clearcontext
    """
    # Clear the context array
    msg_thread = app.get_current_thread()
    num_files = len(msg_thread.context)
    msg_thread.context.clear()
    app.ui.chat_thread_update(msg_thread.thread_id)
    app.ui.print_text(f"Cleared {num_files} file(s) from context.", print_type=PrintType.SUCCESS)
    app.ui.print_text(
        "Note that this doesn't remove context that has already been sent in a message thread's history. In order to "
        "start with fresh context, start a new thread.",
        print_type=PrintType.SUCCESS,
    )
