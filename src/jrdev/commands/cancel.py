#!/usr/bin/env python3

"""
Cancel command implementation for the JrDev terminal.
Cancels active background tasks.
"""

from typing import Any, List
import asyncio

from jrdev.ui import terminal_print, PrintType


async def handle_cancel(terminal: Any, args: List[str]) -> None:
    """
    Handle the /cancel command to cancel background tasks.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (task_id or 'all')
    """
    # Check if there are any active tasks
    if not terminal.active_tasks:
        terminal_print("No active background tasks to cancel.", print_type=PrintType.INFO)
        return
    
    # Parse arguments
    if len(args) < 2:
        terminal_print("Usage: /cancel <task_id>|all", print_type=PrintType.ERROR)
        terminal_print("Example: /cancel abc123", print_type=PrintType.INFO)
        terminal_print("Example: /cancel all", print_type=PrintType.INFO)
        terminal_print("Use /tasks to see active tasks and their IDs.", print_type=PrintType.INFO)
        return
    
    task_id = args[1].lower()
    
    # Cancel all tasks
    if task_id == "all":
        task_count = len(terminal.active_tasks)
        
        # Cancel each task
        for tid, task_info in list(terminal.active_tasks.items()):
            task_info["task"].cancel()
            if tid in terminal.active_tasks:
                del terminal.active_tasks[tid]
        
        terminal_print(f"Cancelled {task_count} background task(s).", print_type=PrintType.SUCCESS)
        return
    
    # Cancel a specific task
    if task_id in terminal.active_tasks:
        task_info = terminal.active_tasks[task_id]
        task_info["task"].cancel()
        del terminal.active_tasks[task_id]
        
        terminal_print(f"Cancelled task #{task_id}.", print_type=PrintType.SUCCESS)
    else:
        terminal_print(f"No task found with ID {task_id}.", print_type=PrintType.ERROR)
        terminal_print("Use /tasks to see active tasks and their IDs.", print_type=PrintType.INFO)