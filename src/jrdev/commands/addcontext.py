#!/usr/bin/env python3

"""
AddContext command implementation for the JrDev terminal.
"""
import glob
import os

from jrdev.ui.ui import terminal_print, PrintType


async def handle_addcontext(terminal, args):
    """
    Handle the /addcontext command to add a file to the LLM context.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (file path or glob pattern)
    """
    if len(args) < 2:
        terminal_print("Error: File path required. Usage: /addcontext <file_path or pattern>", PrintType.ERROR)
        terminal_print("Examples: /addcontext src/file.py, /addcontext src/*.py", PrintType.INFO)
        return

    file_pattern = args[1]
    current_dir = os.getcwd()

    # Use glob to find matching files
    matching_files = glob.glob(os.path.join(current_dir, file_pattern), recursive=True)

    # Also try a direct path match if glob didn't find anything (for files without wildcards)
    if not matching_files and not any(c in file_pattern for c in ['*', '?', '[']):
        full_path = os.path.join(current_dir, file_pattern)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            matching_files = [full_path]

    # Check if we found any files
    if not matching_files:
        terminal_print(f"Error: No files found matching pattern: {file_pattern}", PrintType.ERROR)
        return

    # Filter to regular files only (not directories)
    matching_files = [f for f in matching_files if os.path.isfile(f)]

    if not matching_files:
        terminal_print(f"Error: No files (non-directories) found matching pattern: {file_pattern}", PrintType.ERROR)
        return

    # Process each matching file
    files_added = 0
    files_skipped = 0

    for full_path in matching_files:
        try:
            # Get the relative path for display
            rel_path = os.path.relpath(full_path, current_dir)

            # Read the file content
            with open(full_path, "r") as f:
                file_content = f.read()

            # Limit file size
            if len(file_content) > 2000 * 1024:  # 2MB limit
                size_mb = len(file_content) / (1024 * 1024)
                error_msg = f"Skipping {rel_path}: File too large ({size_mb:.2f} MB) to add to context (max: 2MB)"
                terminal.logger.error(error_msg)
                terminal_print(error_msg, PrintType.ERROR)
                files_skipped += 1
                continue

            # Add the file content to the terminal's context array
            terminal.context.append({
                "name": rel_path,
                "content": file_content
            })

            terminal_print(f"Added: {rel_path}", PrintType.SUCCESS)
            files_added += 1

        except Exception as e:
            terminal_print(f"Error adding file {full_path}: {str(e)}", PrintType.ERROR)
            files_skipped += 1

    if files_added > 0:
        terminal_print(f"Added {files_added} file(s) to context", PrintType.SUCCESS)
        if files_skipped > 0:
            terminal_print(f"Skipped {files_skipped} file(s)", PrintType.WARNING)
        terminal_print(f"Total files in context: {len(terminal.context)}", PrintType.INFO)
    else:
        terminal_print("No files were added to context", PrintType.ERROR)
