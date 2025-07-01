import os
from typing import Any, List

from jrdev.ui.ui import PrintType


async def handle_viewcontext(app: Any, args: List[str], _worker_id: str):
    """
    Displays the files currently loaded into the context window for the active thread.

    When run without arguments, it lists all files in the context with a brief preview.
    To view the full content of a specific file, provide its number from the list.

    Usage:
      /viewcontext - Lists all files in the context.
      /viewcontext <number> - Displays the full content of the specified file.

    Examples:
      /viewcontext
      /viewcontext 2
    """
    # Check if a specific file number was requested
    file_num = None
    if len(args) > 1:
        try:
            file_num = int(args[1]) - 1  # Convert to 0-based index
        except ValueError:
            app.ui.print_text(f"Invalid file number: {args[1]}. Please use a number.", PrintType.ERROR)
            return
    current_context = app.get_current_thread().context
    if not current_context:
        app.ui.print_text(
            "No context files have been added yet. Use /addcontext <file_path> to add files.", PrintType.INFO
        )
        return

    # If a specific file was requested
    if file_num is not None:
        if file_num < 0 or file_num >= len(current_context):
            app.ui.print_text(
                f"Invalid file number. Please use a number between 1 and {len(current_context)}.", PrintType.ERROR
            )
            return

        file_path = current_context[file_num]
        app.ui.print_text(f"Context File {file_num+1}: {file_path}", PrintType.HEADER)

        # Read the file content to display
        try:
            current_dir = os.getcwd()
            full_path = os.path.join(current_dir, file_path)
            with open(full_path, "r", encoding="utf-8") as f:
                file_content = f.read()
            app.ui.print_text(file_content, PrintType.INFO)
        except Exception as e:
            app.ui.print_text(f"Error reading file: {str(e)}", PrintType.ERROR)
        return

    # Otherwise show a summary of all files
    app.ui.print_text("Current context content:", PrintType.HEADER)
    app.ui.print_text(f"Total files in context: {len(current_context)}", PrintType.INFO)

    # Show a summary of files in the context
    app.ui.print_text("Files in context:", PrintType.INFO)
    for i, file_path in enumerate(current_context):
        # Try to read a preview of the content
        try:
            current_dir = os.getcwd()
            full_path = os.path.join(current_dir, file_path)
            with open(full_path, "r", encoding="utf-8") as f:
                preview = f.read(50).replace("\n", " ")
                if os.path.getsize(full_path) > 50:
                    preview += "..."
        except Exception:
            preview = "(unable to read file)"

        app.ui.print_text(f"  {i+1}. {file_path} - {preview}", PrintType.COMMAND)

    app.ui.print_text("\nUse '/viewcontext <number>' to view the full content of a specific file.", PrintType.INFO)
    app.ui.print_text("Use /addcontext <file_path> to add more files to the context.", PrintType.INFO)
    app.ui.print_text("Use /clearcontext to clear all context files.", PrintType.INFO)
