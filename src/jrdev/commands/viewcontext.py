#!/usr/bin/env python3

"""
ViewContext command implementation for the JrDev application.
"""
import os
from typing import Any, List

from jrdev.ui.ui import terminal_print, PrintType


async def handle_viewcontext(app: Any, args: List[str]):
    """
    Handle the /viewcontext command to view the content in the LLM context window.

    Args:
        app: The Application instance
        args: Command arguments (optional file number to view in detail)
    """
    # Check if a specific file number was requested
    file_num = None
    if len(args) > 1:
        try:
            file_num = int(args[1]) - 1  # Convert to 0-based index
        except ValueError:
            terminal_print(f"Invalid file number: {args[1]}. Please use a number.", PrintType.ERROR)
            return
    if not app.context:
        terminal_print("No context files have been added yet. Use /addcontext <file_path> to add files.", PrintType.INFO)
        return

    # If a specific file was requested
    if file_num is not None:
        if file_num < 0 or file_num >= len(app.context):
            terminal_print(f"Invalid file number. Please use a number between 1 and {len(app.context)}.", PrintType.ERROR)
            return

        file_path = app.context[file_num]
        terminal_print(f"Context File {file_num+1}: {file_path}", PrintType.HEADER)
        
        # Read the file content to display
        try:
            current_dir = os.getcwd()
            full_path = os.path.join(current_dir, file_path)
            with open(full_path, "r") as f:
                file_content = f.read()
            terminal_print(file_content, PrintType.INFO)
        except Exception as e:
            terminal_print(f"Error reading file: {str(e)}", PrintType.ERROR)
        return

    # Otherwise show a summary of all files
    terminal_print("Current context content:", PrintType.HEADER)
    terminal_print(f"Total files in context: {len(app.context)}", PrintType.INFO)

    # Show a summary of files in the context
    terminal_print("Files in context:", PrintType.INFO)
    for i, file_path in enumerate(app.context):
        # Try to read a preview of the content
        try:
            current_dir = os.getcwd()
            full_path = os.path.join(current_dir, file_path)
            with open(full_path, "r") as f:
                preview = f.read(50).replace('\n', ' ')
                if os.path.getsize(full_path) > 50:
                    preview += '...'
        except Exception:
            preview = "(unable to read file)"
            
        terminal_print(f"  {i+1}. {file_path} - {preview}", PrintType.COMMAND)

    terminal_print("\nUse '/viewcontext <number>' to view the full content of a specific file.", PrintType.INFO)
    terminal_print("Use /addcontext <file_path> to add more files to the context.", PrintType.INFO)
    terminal_print("Use /clearcontext to clear all context files.", PrintType.INFO)
