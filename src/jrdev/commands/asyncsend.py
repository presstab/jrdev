#!/usr/bin/env python3

"""
AsyncSend command implementation for the JrDev application.
This command sends a message to the LLM and optionally saves the response to a file,
without waiting for the response to be returned to the terminal.
"""

import os
from typing import Any, List

from jrdev.ui.ui import terminal_print, PrintType


async def handle_asyncsend(app: Any, args: List[str]) -> None:
    """
    Handle the /asyncsend command to send a message and optionally save the response to a file.
    This command returns control to the terminal immediately while processing continues in background.

    Args:
        app: The Application instance
        args: Command arguments [filepath] [prompt...]
    """
    import asyncio
    import uuid

    if len(args) < 2:
        terminal_print("Usage: /asyncsend [filepath] <prompt>", print_type=PrintType.ERROR)
        terminal_print("Example: /asyncsend How can I optimize this code?", print_type=PrintType.INFO)
        terminal_print("Example with file: /asyncsend docs/design.md Tell me the design patterns in this codebase",
                      print_type=PrintType.INFO)
        return

    # Generate a unique job ID
    job_id = str(uuid.uuid4())[:8]

    # Check if the first argument is a filepath or part of the prompt
    if len(args) >= 3 and not args[1].startswith("/"):
        filepath = args[1]
        prompt = " ".join(args[2:])

        # Make the filepath absolute if it's relative
        if not os.path.isabs(filepath):
            filepath = os.path.join(os.getcwd(), filepath)

        app.logger.info(f"Starting async task #{job_id} to save response to {filepath}")
        terminal_print(f"Task #{job_id} started: Saving response to {filepath}",
                      print_type=PrintType.INFO)

        # Create a task to process the request in the background
        async def background_task():
            try:
                app.logger.info(f"Background task #{job_id} sending message to model")
                response = await app.send_message(prompt, writepath=filepath, print_stream=False)
                if response:
                    app.logger.info(f"Background task #{job_id} completed successfully")
                else:
                    app.logger.error(f"Background task #{job_id} failed to get response")

                # Task monitor will handle cleanup of completed tasks
            except Exception as e:
                error_msg = str(e)
                app.logger.error(f"Background task #{job_id} failed with error: {error_msg}")
                # Task monitor will handle cleanup of failed tasks

        # Schedule the task but don't wait for it
        task = asyncio.create_task(background_task())
        app.state.active_tasks[job_id] = {
            "task": task,
            "type": "file_response",
            "path": filepath,
            "prompt": prompt[:30] + "..." if len(prompt) > 30 else prompt,
            "timestamp": asyncio.get_event_loop().time()
        }
    else:
        # No filepath provided, just send the message
        prompt = " ".join(args[1:])

        app.logger.info(f"Starting async task #{job_id} to process message")

        # Create a task to process the request in the background
        async def background_task():
            try:
                app.logger.info(f"Background task #{job_id} sending message to model")
                response = await app.send_message(prompt)
                if response:
                    app.logger.info(f"Background task #{job_id} completed successfully")
                else:
                    app.logger.error(f"Background task #{job_id} failed to get response")

                # Task monitor will handle cleanup of completed tasks
            except Exception as e:
                error_msg = str(e)
                app.logger.error(f"Background task #{job_id} failed with error: {error_msg}")

                # Task monitor will handle cleanup of failed tasks

        # Schedule the task but don't wait for it
        task = asyncio.create_task(background_task())
        app.state.active_tasks[job_id] = {
            "task": task,
            "type": "message",
            "prompt": prompt[:30] + "..." if len(prompt) > 30 else prompt,
            "timestamp": asyncio.get_event_loop().time()
        }
