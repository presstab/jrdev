#!/usr/bin/env python3

"""
AddContext command implementation for the JrDev terminal.
"""
import glob
import os
from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_addcontext(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Adds one or more files to the LLM context for the current conversation thread.

    This command makes the content of the specified file(s) available to the LLM
    for subsequent prompts in the current thread. It supports adding single files
    or multiple files using glob patterns.

    Usage:
      /addcontext <file_path_or_glob_pattern>

    Examples:
      /addcontext src/jrdev/core/application.py
      /addcontext "src/jrdev/commands/*.py"
    """
    if len(args) < 2:
        app.ui.print_text("Error: File path required. Usage: /addcontext <file_path or pattern>", PrintType.ERROR)
        app.ui.print_text("Examples: /addcontext src/file.py, /addcontext src/*.py", PrintType.INFO)
        return

    file_pattern = args[1]
    current_dir = os.getcwd()

    # Use glob to find matching files
    matching_files = glob.glob(os.path.join(current_dir, file_pattern), recursive=True)

    # Also try a direct path match if glob didn't find anything (for files without wildcards)
    if not matching_files and not any(c in file_pattern for c in ["*", "?", "["]):
        full_path = os.path.join(current_dir, file_pattern)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            matching_files = [full_path]

    # Check if we found any files
    if not matching_files:
        app.ui.print_text(f"Error: No files found matching pattern: {file_pattern}", PrintType.ERROR)
        return

    # Filter to regular files only (not directories)
    matching_files = [f for f in matching_files if os.path.isfile(f)]

    if not matching_files:
        app.ui.print_text(f"Error: No files (non-directories) found matching pattern: {file_pattern}", PrintType.ERROR)
        return

    # Process each matching file
    files_added = 0
    files_skipped = 0

    current_thread = app.get_current_thread()

    for full_path in matching_files:
        try:
            # Get the relative path for display
            rel_path = os.path.relpath(full_path, current_dir)

            # Just check if file is readable
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    # Just read a small bit to check if file is readable
                    f.read(1)
            except Exception as e:
                error_msg = f"Skipping {rel_path}: Cannot read file: {str(e)}"
                app.logger.error(error_msg)
                app.ui.print_text(error_msg, PrintType.ERROR)
                files_skipped += 1
                continue

            # Add the relative path to the app's context array
            current_thread.add_new_context(rel_path)

            app.ui.print_text(f"Added: {rel_path}", PrintType.SUCCESS)
            files_added += 1

        except Exception as e:
            app.ui.print_text(f"Error adding file {full_path}: {str(e)}", PrintType.ERROR)
            files_skipped += 1

    if files_added > 0:
        app.ui.print_text(f"Added {files_added} file(s) to context", PrintType.SUCCESS)
        if files_skipped > 0:
            app.ui.print_text(f"Skipped {files_skipped} file(s)", PrintType.WARNING)
        app.ui.print_text(f"Total files in context: {len(app.get_current_thread().context)}", PrintType.INFO)
        app.ui.chat_thread_update(current_thread.thread_id)
    else:
        app.ui.print_text("No files were added to context", PrintType.ERROR)
