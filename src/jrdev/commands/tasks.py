#!/usr/bin/env python3

"""
Tasks command implementation for the JrDev application.
Lists all active asynchronous tasks.
"""

import asyncio
from typing import Any, List

from jrdev.ui.ui import terminal_print, PrintType


async def handle_tasks(app: Any, args: List[str]) -> None:
    """
    Handle the /tasks command to display current background tasks.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    if not app.state.active_tasks:
        terminal_print("No active background tasks.", print_type=PrintType.INFO)
        return

    terminal_print("\nActive Background Tasks:", print_type=PrintType.HEADER)

    current_time = asyncio.get_event_loop().time()
    for task_id, task_info in app.state.active_tasks.items():
        # Calculate how long the task has been running
        elapsed = current_time - task_info["timestamp"]
        elapsed_str = format_time(elapsed)

        # Display task information
        terminal_print(f"  Task #{task_id} ({elapsed_str})", print_type=PrintType.INFO)

        if task_info["type"] == "file_response":
            terminal_print(f"    Type: Response → File", print_type=PrintType.INFO)
            terminal_print(f"    Path: {task_info['path']}", print_type=PrintType.INFO)
        else:
            terminal_print(f"    Type: Message", print_type=PrintType.INFO)
            terminal_print(f"    Prompt: {task_info['prompt']}", print_type=PrintType.INFO)
        terminal_print("", print_type=PrintType.INFO)


def format_time(seconds: float) -> str:
    """Format seconds into a readable time string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        sec_remainder = seconds % 60
        return f"{int(minutes)}m {int(sec_remainder)}s"
    else:
        hours = seconds // 3600
        min_remainder = (seconds % 3600) // 60
        return f"{int(hours)}h {int(min_remainder)}m"
