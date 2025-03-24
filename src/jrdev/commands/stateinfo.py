#!/usr/bin/env python3

"""
Stateinfo command implementation for the JrDev terminal.
Displays current terminal state information.
"""

from jrdev.file_utils import JRDEV_DIR
from jrdev.ui.ui import terminal_print, PrintType


async def handle_stateinfo(terminal, args):
    """
    Handle the /stateinfo command to display current terminal state.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal_print("\nCurrent Terminal State:", print_type=PrintType.HEADER)
    terminal_print(f"  Model: {terminal.model}", print_type=PrintType.INFO)
    
    # Display message history count
    message_count = len(terminal.message_history)
    terminal_print(f"  Total messages: {message_count}", print_type=PrintType.INFO)
    
    # Display file processing status
    processing_status = "Enabled" if terminal.process_follow_up else "Disabled"
    status_type = PrintType.SUCCESS if terminal.process_follow_up else PrintType.WARNING
    terminal_print(f"  File processing: {processing_status}", print_type=status_type)
    
    # Display context file count
    context_count = len(terminal.context)
    terminal_print(f"  Context files: {context_count}", print_type=PrintType.INFO)
    
    # Display API details
    if terminal.venice_client:
        terminal_print(f"  Venice API base URL: {terminal.venice_client.base_url}", print_type=PrintType.INFO)
    if terminal.openai_client:
        terminal_print(f"  OpenAI API configured", print_type=PrintType.INFO)
    
    # If the terminal has any file context loaded
    project_files = {
        "filetree": f"{JRDEV_DIR}jrdev_filetree.txt",
        "filecontext": f"{JRDEV_DIR}jrdev_filecontext.md",
        "overview": f"{JRDEV_DIR}jrdev_overview.md",
    }
    
    loaded_files = []
    for key, filename in project_files.items():
        if any(key in msg.get("content", "") for msg in terminal.messages if msg.get("role") == "user"):
            loaded_files.append(filename)
    
    if loaded_files:
        terminal_print(f"  Project context: {', '.join(loaded_files)}", print_type=PrintType.INFO)
    else:
        terminal_print(f"  Project context: None", print_type=PrintType.INFO)