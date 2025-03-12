#!/usr/bin/env python3

"""
AsyncSend command implementation for the JrDev terminal.
This command sends a message to the LLM and optionally saves the response to a file,
without waiting for the response to be returned to the terminal.
"""

from typing import Any, List
import os

from jrdev.ui import terminal_print, PrintType


async def handle_asyncsend(terminal: Any, args: List[str]) -> None:
    """
    Handle the /asyncsend command to send a message and optionally save the response to a file.
    This command returns control to the terminal immediately while processing continues in background.

    Args:
        terminal: The JrDevTerminal instance
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
            
        terminal_print(f"Task #{job_id} started: Saving response to {filepath}", 
                      print_type=PrintType.INFO)
                      
        # Create a task to process the request in the background
        async def background_task():
            try:
                response = await terminal.send_message(prompt, writepath=filepath)
                if response:
                    terminal_print(f"Task #{job_id} completed: Response saved to {filepath}", 
                                  print_type=PrintType.SUCCESS)
                else:
                    terminal_print(f"Task #{job_id} failed: Error sending message or writing to file", 
                                  print_type=PrintType.ERROR)
                
                # Remove task from active tasks on completion
                if job_id in terminal.active_tasks:
                    del terminal.active_tasks[job_id]
            except Exception as e:
                terminal_print(f"Task #{job_id} failed: {str(e)}", 
                              print_type=PrintType.ERROR)
                
                # Remove task from active tasks on error
                if job_id in terminal.active_tasks:
                    del terminal.active_tasks[job_id]
        
        # Schedule the task but don't wait for it
        task = asyncio.create_task(background_task())
        terminal.active_tasks[job_id] = {"task": task, "type": "file_response", "path": filepath, "timestamp": asyncio.get_event_loop().time()}
    else:
        # No filepath provided, just send the message
        prompt = " ".join(args[1:])
        
        terminal_print(f"Task #{job_id} started: Processing in background", 
                      print_type=PrintType.INFO)
        
        # Create a task to process the request in the background
        async def background_task():
            try:
                response = await terminal.send_message(prompt)
                if response:
                    terminal_print(f"Task #{job_id} completed", 
                                  print_type=PrintType.SUCCESS)
                else:
                    terminal_print(f"Task #{job_id} failed: Error sending message", 
                                  print_type=PrintType.ERROR)
                
                # Remove task from active tasks on completion
                if job_id in terminal.active_tasks:
                    del terminal.active_tasks[job_id]
            except Exception as e:
                terminal_print(f"Task #{job_id} failed: {str(e)}", 
                              print_type=PrintType.ERROR)
                
                # Remove task from active tasks on error
                if job_id in terminal.active_tasks:
                    del terminal.active_tasks[job_id]
        
        # Schedule the task but don't wait for it
        task = asyncio.create_task(background_task())
        terminal.active_tasks[job_id] = {"task": task, "type": "message", "prompt": prompt[:30] + "...", "timestamp": asyncio.get_event_loop().time()}