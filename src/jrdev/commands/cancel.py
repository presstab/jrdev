#!/usr/bin/env python3

"""
Cancel command implementation for the JrDev application.
Cancels active background tasks.
"""

from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_cancel(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Cancels active background tasks.

    This command can stop a single running task by its ID or all active tasks.
    Use the `/tasks` command to see a list of active tasks and their IDs.

    Usage:
      /cancel <task_id>
      /cancel all
    """
    # Check if there are any active tasks
    if not app.state.active_tasks:
        app.ui.print_text("No active background tasks to cancel.", print_type=PrintType.INFO)
        return

    # Parse arguments
    if len(args) < 2:
        app.ui.print_text("Usage: /cancel <task_id>|all", print_type=PrintType.ERROR)
        app.ui.print_text("Example: /cancel abc123", print_type=PrintType.INFO)
        app.ui.print_text("Example: /cancel all", print_type=PrintType.INFO)
        app.ui.print_text("Use /tasks to see active tasks and their IDs.", print_type=PrintType.INFO)
        return

    task_id = args[1].lower()

    # Cancel all tasks
    if task_id == "all":
        task_count = len(app.state.active_tasks)

        # Cancel each task
        for tid, task_info in list(app.state.active_tasks.items()):
            task_info["task"].cancel()
            if tid in app.state.active_tasks:
                del app.state.active_tasks[tid]

        app.ui.print_text(f"Cancelled {task_count} background task(s).", print_type=PrintType.SUCCESS)
        return

    # Cancel a specific task
    if task_id in app.state.active_tasks:
        task_info = app.state.active_tasks[task_id]
        task_info["task"].cancel()
        del app.state.active_tasks[task_id]

        app.ui.print_text(f"Cancelled task #{task_id}.", print_type=PrintType.SUCCESS)
    else:
        app.ui.print_text(f"No task found with ID {task_id}.", print_type=PrintType.ERROR)
        app.ui.print_text("Use /tasks to see active tasks and their IDs.", print_type=PrintType.INFO)
