#!/usr/bin/env python3

"""
Stateinfo command implementation for the JrDev application.
Displays current application state information.
"""

from typing import Any, List

from jrdev.file_utils import JRDEV_DIR
from jrdev.ui.ui import PrintType


async def handle_stateinfo(app: Any, args: List[str], worker_id: str) -> None:
    """
    Handle the /stateinfo command to display current application state.

    Args:
        app: The Application instance
        args: Command arguments (unused)
    """
    app.ui.print_text("\nCurrent Application State:", print_type=PrintType.HEADER)
    app.ui.print_text(f"  Model: {app.state.model}", print_type=PrintType.INFO)
    
    # Display message history count
    current_thread = app.get_current_thread()
    message_count = len(current_thread.messages)
    app.ui.print_text(f"  Total messages: {message_count}", print_type=PrintType.INFO)

    # Display context file count
    context_count = len(current_thread.context)
    app.ui.print_text(f"  Context files: {context_count}", print_type=PrintType.INFO)
    # Show context files if any exist
    if context_count > 0:
        for ctx_file in current_thread.context:
            app.ui.print_text(f"    - {ctx_file}", print_type=PrintType.INFO)
    else:
        app.ui.print_text(f"  Context files: 0", print_type=PrintType.INFO)
    
    # Display API details
    if app.state.clients and app.state.clients.venice:
        app.ui.print_text(f"  Venice API base URL: {app.state.clients.venice.base_url}", print_type=PrintType.INFO)
    if app.state.clients and app.state.clients.openai:
        app.ui.print_text(f"  OpenAI API configured", print_type=PrintType.INFO)
    
    # If the app has any file context loaded
    project_files = {
        "filetree": f"{JRDEV_DIR}jrdev_filetree.txt",
        "filecontext": f"{JRDEV_DIR}jrdev_filecontext.md",
        "overview": f"{JRDEV_DIR}jrdev_overview.md",
    }
    
    loaded_files = []
    for key, filename in project_files.items():
        if any(key in msg.get("content", "") for msg in current_thread.messages if msg.get("role") == "user"):
            loaded_files.append(filename)
    
    if loaded_files:
        app.ui.print_text(f"  Project context: {', '.join(loaded_files)}", print_type=PrintType.INFO)
    else:
        app.ui.print_text(f"  Project context: None", print_type=PrintType.INFO)
    
    # Show Context Manager information
    if hasattr(app, 'context_manager') and app.context_manager:
        # Get number of tracked files in the context manager
        tracked_file_count = len(app.context_manager.index.get("files", {}))
        app.ui.print_text(f"  Context manager tracked files: {tracked_file_count}", print_type=PrintType.INFO)