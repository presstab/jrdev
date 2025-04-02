#!/usr/bin/env python3

"""
Project context command implementation for the JrDev terminal.
"""

import os
from typing import Any, Dict, List

from jrdev.ui.ui import PrintType, terminal_print


async def handle_projectcontext(app: Any, args: List[str]) -> None:
    """
    Handle the /projectcontext command for managing project context.

    Commands:
        /projectcontext about - Display information about project context
        /projectcontext on|off - Toggle using project context in requests
        /projectcontext status - Show current status of project context
        /projectcontext list - List all tracked files in context
        /projectcontext view <filepath> - View context for a specific file
        /projectcontext refresh <filepath> - Refresh context for a specific file
        /projectcontext add <filepath> - Add and index a file to the context
        /projectcontext remove <filepath> - Remove a file from the context
        /projectcontext help - Show usage information

    Args:
        app: The Application instance
        args: Command arguments
    """
    if len(args) < 2:
        _show_usage()
        return

    command = args[1].lower()

    if command == "about":
        _show_about_info()

    elif command == "help":
        _show_usage()

    elif command == "on":
        app.state.use_project_context = True
        terminal_print("Project context is now ON", PrintType.SUCCESS)

    elif command == "off":
        app.state.use_project_context = False
        terminal_print("Project context is now OFF", PrintType.SUCCESS)

    elif command == "status":
        await _show_status(app)

    elif command == "list":
        await _list_context_files(app)

    elif command == "view" and len(args) > 2:
        await _view_file_context(app, args[2])

    elif command == "refresh" and len(args) > 2:
        await _refresh_file_context(app, args[2])

    elif command == "add" and len(args) > 2:
        await _add_file_to_context(app, args[2])

    elif command == "remove" and len(args) > 2:
        await _remove_file_from_context(app, args[2])

    else:
        _show_usage()


def _show_about_info() -> None:
    """
    Display information about what project context is and how to use it.
    """
    terminal_print("About Project Context", PrintType.HEADER)
    terminal_print(
        "Project contexts are token-efficient compacted summaries of key files in your project.",
        PrintType.INFO,
    )
    terminal_print(
        "These summaries are included in most communications with AI models and allow the AI",
        PrintType.INFO,
    )
    terminal_print(
        "to quickly and cost-efficiently become familiar with your project structure and conventions.",
        PrintType.INFO,
    )
    terminal_print("", PrintType.INFO)
    terminal_print("Best Practices:", PrintType.HEADER)
    terminal_print(
        "- Include the most important/central files in your project",
        PrintType.INFO,
    )
    terminal_print(
        "- Add files that define core abstractions, APIs, or project conventions",
        PrintType.INFO,
    )
    terminal_print(
        "- Some AI communications include all project context files, so the list should be efficient",
        PrintType.INFO,
    )
    terminal_print(
        "- Use '/projectcontext add <filepath>' to add files you feel are missing",
        PrintType.INFO,
    )
    terminal_print(
        "- Use '/projectcontext remove <filepath>' to remove files that aren't mission-critical",
        PrintType.INFO,
    )
    terminal_print("", PrintType.INFO)
    terminal_print("Management:", PrintType.HEADER)
    terminal_print(
        "- Toggle project context on/off with '/projectcontext on' or '/projectcontext off'",
        PrintType.INFO,
    )
    terminal_print(
        "- Check status with '/projectcontext status' or list files with '/projectcontext list'",
        PrintType.INFO,
    )


def _show_usage() -> None:
    """
    Show usage information for the projectcontext command.
    """
    terminal_print("Project Context Command Usage:", PrintType.HEADER)
    terminal_print(
        "/projectcontext about - Display information about project context",
        PrintType.INFO,
    )
    terminal_print(
        "/projectcontext on|off - Toggle using project context in requests",
        PrintType.INFO,
    )
    terminal_print(
        "/projectcontext status - Show current status of project context",
        PrintType.INFO,
    )
    terminal_print(
        "/projectcontext list - List all tracked files in project context", PrintType.INFO
    )
    terminal_print(
        "/projectcontext view <filepath> - View context for a specific file",
        PrintType.INFO,
    )
    terminal_print(
        "/projectcontext refresh <filepath> - Refresh context for a specific file",
        PrintType.INFO,
    )
    terminal_print(
        "/projectcontext add <filepath> - Add and index a file to the project context",
        PrintType.INFO,
    )
    terminal_print(
        "/projectcontext remove <filepath> - Remove a file from the project context",
        PrintType.INFO,
    )
    terminal_print(
        "/projectcontext help - Show this usage information",
        PrintType.INFO,
    )


async def _show_status(app: Any) -> None:
    """
    Show the current status of the project context system.

    Args:
        app: The Application instance
    """
    context_manager = app.state.context_manager
    file_count = len(context_manager.index.get("files", {}))
    outdated_files = context_manager.get_outdated_files()

    terminal_print("Project Context Status:", PrintType.HEADER)
    terminal_print(f"Context enabled: {app.state.use_project_context}", PrintType.INFO)
    terminal_print(f"Files tracked: {file_count}", PrintType.INFO)
    terminal_print(f"Outdated files: {len(outdated_files)}", PrintType.INFO)

    if outdated_files:
        terminal_print("\nOutdated files that need refreshing:", PrintType.WARNING)
        for file in outdated_files[:10]:  # Show at most 10 files
            terminal_print(f"- {file}", PrintType.INFO)

        if len(outdated_files) > 10:
            terminal_print(f"... and {len(outdated_files) - 10} more", PrintType.INFO)


async def _list_context_files(app: Any) -> None:
    """
    List all files tracked in the context system.

    Args:
        app: The Application instance
    """
    context_manager = app.state.context_manager
    files = list(context_manager.index.get("files", {}).keys())

    if not files:
        terminal_print("No files in project context", PrintType.WARNING)
        return

    terminal_print(f"Tracked Files ({len(files)}):", PrintType.HEADER)

    # Group files by directory for better organization
    dir_to_files: Dict[str, List[str]] = {}
    for file in files:
        directory = os.path.dirname(file) or "."
        if directory not in dir_to_files:
            dir_to_files[directory] = []
        dir_to_files[directory].append(os.path.basename(file))

    # Print files grouped by directory
    for directory, filenames in sorted(dir_to_files.items()):
        terminal_print(f"\n{directory}/", PrintType.INFO)
        for filename in sorted(filenames):
            terminal_print(f"  - {filename}", PrintType.INFO)


async def _view_file_context(app: Any, file_path: str) -> None:
    """
    View the context for a specific file.

    Args:
        app: The Application instance
        file_path: Path to the file to view context for
    """
    context_manager = app.state.context_manager
    context = context_manager._read_context_file(file_path)

    if not context:
        terminal_print(f"No context found for {file_path}", PrintType.WARNING)
        return

    terminal_print(f"Context for {file_path}:", PrintType.HEADER)
    terminal_print(context, PrintType.INFO)


async def _refresh_file_context(app: Any, file_path: str) -> None:
    """
    Refresh the context for a specific file.

    Args:
        app: The Application instance
        file_path: Path to the file to refresh context for
    """
    if not os.path.exists(file_path):
        terminal_print(f"File not found: {file_path}", PrintType.ERROR)
        return

    terminal_print(f"Refreshing context for {file_path}...", PrintType.PROCESSING)

    # Use the context manager to regenerate the context
    analysis = await app.state.context_manager.generate_context(file_path, app)

    if analysis:
        terminal_print(
            f"Successfully refreshed context for {file_path}", PrintType.SUCCESS
        )
    else:
        terminal_print(f"Failed to refresh context for {file_path}", PrintType.ERROR)


async def _add_file_to_context(app: Any, file_path: str) -> None:
    """
    Add a file to the context system and generate its initial analysis.

    Args:
        app: The Application instance
        file_path: Path to the file to add to the context
    """
    if not os.path.exists(file_path):
        terminal_print(f"File not found: {file_path}", PrintType.ERROR)
        return

    context_manager = app.state.context_manager

    # Check if file is already in the index
    if file_path in context_manager.index.get("files", {}):
        terminal_print(f"File already tracked: {file_path}", PrintType.WARNING)
        terminal_print("Refreshing context instead...", PrintType.INFO)
        await _refresh_file_context(app, file_path)
        return

    terminal_print(
        f"Adding {file_path} to project context and generating analysis...",
        PrintType.PROCESSING,
    )

    # Generate context for the file and add it to the index
    analysis = await context_manager.generate_context(file_path, app)

    if analysis:
        terminal_print(f"Successfully added {file_path} to project context", PrintType.SUCCESS)
    else:
        terminal_print(f"Failed to add {file_path} to project context", PrintType.ERROR)


async def _remove_file_from_context(app: Any, file_path: str) -> None:
    """
    Remove a file from the context system.

    Args:
        app: The Application instance
        file_path: Path to the file to remove from the context
    """
    context_manager = app.state.context_manager

    # Check if file is in the index
    if file_path not in context_manager.index.get("files", {}):
        terminal_print(f"File not found in project context: {file_path}", PrintType.ERROR)
        return

    try:
        # Get the context file path to delete it
        context_file_path = context_manager._get_context_path(file_path)

        # Remove from the index
        if (
            "files" in context_manager.index
            and file_path in context_manager.index["files"]
        ):
            del context_manager.index["files"][file_path]
            context_manager._save_index()

        # Delete the context file if it exists
        if os.path.exists(context_file_path):
            os.remove(context_file_path)

        terminal_print(
            f"Successfully removed {file_path} from project context", PrintType.SUCCESS
        )
    except Exception as e:
        terminal_print(
            f"Error removing {file_path} from project context: {str(e)}", PrintType.ERROR
        )
