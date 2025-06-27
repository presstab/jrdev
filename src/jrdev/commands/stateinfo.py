#!/usr/bin/env python3

"""
Stateinfo command implementation for the JrDev application.
Displays current application state information.
"""

from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_stateinfo(app: Any, _args: List[str], _worker_id: str) -> None:
    """
    Displays a snapshot of the current application and thread state for debugging.

    This command provides diagnostic information, including the currently active model,
    the number of messages in the current thread, the files in the context window,
    and the number of files tracked by the persistent project context manager.

    Usage:
      /stateinfo
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
        app.ui.print_text("  Context files: 0", print_type=PrintType.INFO)

    # If the app has any file context loaded
    project_files = app.state.project_files

    loaded_files = []
    for key, filename in project_files.items():
        if any(key in msg.get("content", "") for msg in current_thread.messages if msg.get("role") == "user"):
            loaded_files.append(filename)

    if loaded_files:
        app.ui.print_text(f"  Project context: {', '.join(loaded_files)}", print_type=PrintType.INFO)
    else:
        app.ui.print_text("  Project context: None", print_type=PrintType.INFO)

    # Show Context Manager information
    if hasattr(app, "context_manager") and app.context_manager:
        # Get number of tracked files in the context manager
        tracked_file_count = len(app.context_manager.index.get("files", {}))
        app.ui.print_text(f"  Context manager tracked files: {tracked_file_count}", print_type=PrintType.INFO)
