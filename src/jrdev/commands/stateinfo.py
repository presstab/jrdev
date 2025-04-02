#!/usr/bin/env python3

"""
Stateinfo command implementation for the JrDev application.
Displays current application state information.
"""

from typing import Any, List

from jrdev.file_utils import JRDEV_DIR
from jrdev.ui.ui import terminal_print, PrintType


async def handle_stateinfo(app: Any, args: List[str]) -> None:
    """
    Handle the /stateinfo command to display current application state.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    terminal_print("\nCurrent Application State:", print_type=PrintType.HEADER)
    terminal_print(f"  Model: {app.state.model}", print_type=PrintType.INFO)
    
    # Display message history count
    messages = app.message_history() if callable(getattr(app, 'message_history', None)) else app.state.messages
    message_count = len(messages)
    terminal_print(f"  Total messages: {message_count}", print_type=PrintType.INFO)
    
    
    # Display context file count
    if hasattr(app.state, 'context') and isinstance(app.state.context, list):
        context_count = len(app.state.context)
        terminal_print(f"  Context files: {context_count}", print_type=PrintType.INFO)
        # Show context files if any exist
        if context_count > 0:
            for ctx_file in app.state.context:
                terminal_print(f"    - {ctx_file}", print_type=PrintType.INFO)
    else:
        terminal_print(f"  Context files: 0", print_type=PrintType.INFO)
    
    # Display API details
    if app.state.clients and app.state.clients.venice:
        terminal_print(f"  Venice API base URL: {app.state.clients.venice.base_url}", print_type=PrintType.INFO)
    if app.state.clients and app.state.clients.openai:
        terminal_print(f"  OpenAI API configured", print_type=PrintType.INFO)
    
    # If the app has any file context loaded
    project_files = {
        "filetree": f"{JRDEV_DIR}jrdev_filetree.txt",
        "filecontext": f"{JRDEV_DIR}jrdev_filecontext.md",
        "overview": f"{JRDEV_DIR}jrdev_overview.md",
    }
    
    loaded_files = []
    for key, filename in project_files.items():
        if any(key in msg.get("content", "") for msg in app.state.messages if msg.get("role") == "user"):
            loaded_files.append(filename)
    
    if loaded_files:
        terminal_print(f"  Project context: {', '.join(loaded_files)}", print_type=PrintType.INFO)
    else:
        terminal_print(f"  Project context: None", print_type=PrintType.INFO)
    
    # Show Context Manager information
    if hasattr(app, 'context_manager') and app.context_manager:
        # Get number of tracked files in the context manager
        tracked_file_count = len(app.context_manager.index.get("files", {}))
        terminal_print(f"  Context manager tracked files: {tracked_file_count}", print_type=PrintType.INFO)