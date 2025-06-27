#!/usr/bin/env python3

"""
Tasks command implementation for the JrDev application.
Lists all active asynchronous tasks.
"""

import asyncio
from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_tasks(app: Any, _args: List[str], _worker_id: str) -> None:
    """
    Lists all currently active background tasks.

    This command displays information about tasks running in the background,
    such as those initiated by `/asyncsend` or `/code`. It shows the task ID,
    its type, a brief description, and its running time.

    Usage:
      /tasks
    """
    if not app.state.active_tasks:
        app.ui.print_text("No active background tasks.", print_type=PrintType.INFO)
        return

    app.ui.print_text("\nActive Background Tasks:", print_type=PrintType.HEADER)

    current_time = asyncio.get_event_loop().time()
    for task_id, task_info in app.state.active_tasks.items():
        # Calculate how long the task has been running
        elapsed = current_time - task_info["timestamp"]
        elapsed_str = format_time(elapsed)

        # Display task information
        app.ui.print_text(f"  Task #{task_id} ({elapsed_str})", print_type=PrintType.INFO)

        if task_info["type"] == "file_response":
            app.ui.print_text("    Type: Response → File", print_type=PrintType.INFO)
            app.ui.print_text(f"    Path: {task_info['path']}", print_type=PrintType.INFO)
        else:
            app.ui.print_text("    Type: Message", print_type=PrintType.INFO)
            app.ui.print_text(f"    Prompt: {task_info['prompt']}", print_type=PrintType.INFO)
        app.ui.print_text("", print_type=PrintType.INFO)


def format_time(seconds: float) -> str:
    """Format seconds into a readable time string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        minutes = seconds // 60
        sec_remainder = seconds % 60
        return f"{int(minutes)}m {int(sec_remainder)}s"

    hours = seconds // 3600
    min_remainder = (seconds % 3600) // 60
    return f"{int(hours)}h {int(min_remainder)}m"
