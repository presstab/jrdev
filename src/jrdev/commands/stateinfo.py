#!/usr/bin/env python3

"""
Stateinfo command implementation for the JrDev terminal.
Displays current terminal state information.
"""

from typing import Any, List

from jrdev.file_utils import JRDEV_DIR
from jrdev.ui.ui import terminal_print, PrintType


async def handle_stateinfo(terminal: Any, args: List[str]) -> None:
    """
    Handle the /stateinfo command to display current terminal state.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal_print("\nCurrent Terminal State:", print_type=PrintType.HEADER)
    terminal_print(f"  Model: {terminal.model}", print_type=PrintType.INFO)
    
    # Display message history count
    messages = terminal.message_history() if callable(getattr(terminal, 'message_history', None)) else terminal.messages
    message_count = len(messages)
    terminal_print(f"  Total messages: {message_count}", print_type=PrintType.INFO)
    
    
    # Display context file count
    if isinstance(terminal.context, list):
        context_count = len(terminal.context)
        terminal_print(f"  Context files: {context_count}", print_type=PrintType.INFO)
        # Show context files if any exist
        if context_count > 0:
            for ctx_file in terminal.context:
                terminal_print(f"    - {ctx_file}", print_type=PrintType.INFO)
    else:
        terminal_print(f"  Context files: 0", print_type=PrintType.INFO)
    
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
    
    # Show Context Manager information
    if hasattr(terminal, 'context_manager') and terminal.context_manager:
        # Get number of tracked files in the context manager
        tracked_file_count = len(terminal.context_manager.index.get("files", {}))
        terminal_print(f"  Context manager tracked files: {tracked_file_count}", print_type=PrintType.INFO)