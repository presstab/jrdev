import os
from typing import Any, Dict, List

from jrdev.ui.ui import PrintType


# pylint: disable=too-many-branches
async def handle_projectcontext(app: Any, args: List[str], worker_id: str) -> None:
    """
    Manages the persistent, token-efficient project context.

    This context consists of AI-generated summaries of key project files, which are
    used to give the AI long-term awareness of the project's architecture and
    conventions without consuming excessive tokens.

    Usage:
      /projectcontext <subcommand> [arguments]

    Subcommands:
      about                  - Display information about project context.
      on|off                 - Toggle using project context in requests.
      status                 - Show current status, including outdated files.
      list                   - List all files tracked in the project context.
      view <filepath>        - View the summarized context for a specific file.
      update                 - Refresh context for all tracked files that are out of date.
      refresh <filepath>     - Force a refresh of the context for a specific file.
      add <filepath>         - Add and index a new file to the project context.
      remove <filepath>      - Remove a file from the project context.
      help                   - Show this usage information.
    """
    if len(args) < 2:
        _show_usage(app)
        return

    command = args[1].lower()

    if command == "about":
        _show_about_info(app)

    elif command == "help":
        _show_usage(app)

    elif command == "on":
        app.state.use_project_context = True
        app.ui.print_text("Project context is now ON", PrintType.SUCCESS)
        app.ui.project_context_changed(is_enabled=True)

    elif command == "off":
        app.state.use_project_context = False
        app.ui.print_text("Project context is now OFF", PrintType.SUCCESS)
        app.ui.project_context_changed(is_enabled=False)

    elif command == "status":
        await _show_status(app)

    elif command == "list":
        await _list_context_files(app)

    elif command == "view" and len(args) > 2:
        await _view_file_context(app, args[2])

    elif command == "update":
        await _update_outdated_context_files(app, worker_id)

    elif command == "refresh" and len(args) > 2:
        await _refresh_file_context(app, args[2])

    elif command == "add" and len(args) > 2:
        await _add_file_to_context(app, args[2])

    elif command == "remove" and len(args) > 2:
        await _remove_file_from_context(app, args[2])

    else:
        _show_usage(app)


def _show_about_info(app: Any) -> None:
    """
    Display information about what project context is and how to use it.
    """
    app.ui.print_text("About Project Context", PrintType.HEADER)
    app.ui.print_text(
        "Project contexts are token-efficient compacted summaries of key files in your project.",
        PrintType.INFO,
    )
    app.ui.print_text(
        "These summaries are included in most communications with AI models and allow the AI",
        PrintType.INFO,
    )
    app.ui.print_text(
        "to quickly and cost-efficiently become familiar with your project structure and conventions.",
        PrintType.INFO,
    )
    app.ui.print_text("", PrintType.INFO)
    app.ui.print_text("Best Practices:", PrintType.HEADER)
    app.ui.print_text(
        "- Include the most important/central files in your project",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- Add files that define core abstractions, APIs, or project conventions",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- Some AI communications include all project context files, so the list should be efficient",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- Use '/projectcontext add <filepath>' to add files you feel are missing",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- Use '/projectcontext remove <filepath>' to remove files that aren't mission-critical",
        PrintType.INFO,
    )
    app.ui.print_text("", PrintType.INFO)
    app.ui.print_text("Management:", PrintType.HEADER)
    app.ui.print_text(
        "- Toggle project context on/off with '/projectcontext on' or '/projectcontext off'",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- Check status with '/projectcontext status' or list files with '/projectcontext list'",
        PrintType.INFO,
    )


def _show_usage(app: Any) -> None:
    """
    Show usage information for the projectcontext command.
    """
    app.ui.print_text("Project Context Command Usage:", PrintType.HEADER)
    app.ui.print_text(
        "/projectcontext about - Display information about project context",
        PrintType.INFO,
    )
    app.ui.print_text(
        "/projectcontext on|off - Toggle using project context in requests",
        PrintType.INFO,
    )
    app.ui.print_text(
        "/projectcontext status - Show current status of project context",
        PrintType.INFO,
    )
    app.ui.print_text("/projectcontext list - List all tracked files in project context", PrintType.INFO)
    app.ui.print_text(
        "/projectcontext view <filepath> - View context for a specific file",
        PrintType.INFO,
    )
    app.ui.print_text(
        "/projectcontext update - Refresh context for tracked files that are out of date",
        PrintType.INFO,
    )
    app.ui.print_text(
        "/projectcontext refresh <filepath> - Refresh context for a specific file",
        PrintType.INFO,
    )
    app.ui.print_text(
        "/projectcontext add <filepath> - Add and index a file to the project context",
        PrintType.INFO,
    )
    app.ui.print_text(
        "/projectcontext remove <filepath> - Remove a file from the project context",
        PrintType.INFO,
    )
    app.ui.print_text(
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

    app.ui.print_text("Project Context Status:", PrintType.HEADER)
    app.ui.print_text(f"Context enabled: {app.state.use_project_context}", PrintType.INFO)
    app.ui.print_text(f"Files tracked: {file_count}", PrintType.INFO)
    app.ui.print_text(f"Outdated files: {len(outdated_files)}", PrintType.INFO)

    if outdated_files:
        app.ui.print_text("\nOutdated files that need refreshing:", PrintType.WARNING)
        for file in outdated_files[:10]:  # Show at most 10 files
            app.ui.print_text(f"- {file}", PrintType.INFO)

        if len(outdated_files) > 10:
            app.ui.print_text(f"... and {len(outdated_files) - 10} more", PrintType.INFO)


async def _list_context_files(app: Any) -> None:
    """
    List all files tracked in the context system.

    Args:
        app: The Application instance
    """
    context_manager = app.state.context_manager
    files = list(context_manager.index.get("files", {}).keys())

    if not files:
        app.ui.print_text("No files in project context", PrintType.WARNING)
        return

    app.ui.print_text(f"Tracked Files ({len(files)}):", PrintType.HEADER)

    # Group files by directory for better organization
    dir_to_files: Dict[str, List[str]] = {}
    for file in files:
        directory = os.path.dirname(file) or "."
        if directory not in dir_to_files:
            dir_to_files[directory] = []
        dir_to_files[directory].append(os.path.basename(file))

    # Print files grouped by directory
    for directory, filenames in sorted(dir_to_files.items()):
        app.ui.print_text(f"\n{directory}/", PrintType.INFO)
        for filename in sorted(filenames):
            app.ui.print_text(f"  - {filename}", PrintType.INFO)


async def _view_file_context(app: Any, file_path: str) -> None:
    """
    View the context for a specific file.

    Args:
        app: The Application instance
        file_path: Path to the file to view context for
    """
    context_manager = app.state.context_manager
    context = context_manager.read_context_file(file_path)

    if not context:
        app.ui.print_text(f"No context found for {file_path}", PrintType.WARNING)
        return

    app.ui.print_text(f"Context for {file_path}:", PrintType.HEADER)
    app.ui.print_text(context, PrintType.INFO)


async def _refresh_file_context(app: Any, file_path: str) -> None:
    """
    Refresh the context for a specific file.

    Args:
        app: The Application instance
        file_path: Path to the file to refresh context for
    """
    if not os.path.exists(file_path):
        app.ui.print_text(f"File not found: {file_path}", PrintType.ERROR)
        return

    app.ui.print_text(f"Refreshing context for {file_path}...", PrintType.PROCESSING)

    # Use the context manager to regenerate the context
    analysis = await app.state.context_manager.generate_context(file_path, app)

    if analysis:
        app.ui.print_text(f"Successfully refreshed context for {file_path}", PrintType.SUCCESS)
    else:
        app.ui.print_text(f"Failed to refresh context for {file_path}", PrintType.ERROR)


async def _add_file_to_context(app: Any, file_path: str) -> None:
    """
    Add a file to the context system and generate its initial analysis.

    Args:
        app: The Application instance
        file_path: Path to the file to add to the context
    """
    if not os.path.exists(file_path):
        app.ui.print_text(f"File not found: {file_path}", PrintType.ERROR)
        return

    context_manager = app.state.context_manager

    # Check if file is already in the index
    if file_path in context_manager.index.get("files", {}):
        app.ui.print_text(f"File already tracked: {file_path}", PrintType.WARNING)
        app.ui.print_text("Refreshing context instead...", PrintType.INFO)
        await _refresh_file_context(app, file_path)
        return

    app.ui.print_text(
        f"Adding {file_path} to project context and generating analysis...",
        PrintType.PROCESSING,
    )

    # Generate context for the file and add it to the index
    analysis = await context_manager.generate_context(file_path, app)

    if analysis:
        app.ui.print_text(f"Successfully added {file_path} to project context", PrintType.SUCCESS)
    else:
        app.ui.print_text(f"Failed to add {file_path} to project context", PrintType.ERROR)


async def _update_outdated_context_files(app: Any, worker_id: str) -> None:
    """
    Refresh context for all tracked files in the project context.

    Args:
        app: The Application instance
        worker_id: Worker ID for task tracking
    """
    context_manager = app.state.context_manager
    files = context_manager.get_outdated_files()

    if not files:
        app.ui.print_text("No files in project context to update", PrintType.WARNING)
        return

    app.ui.print_text(f"Updating context for all {len(files)} tracked files...", PrintType.PROCESSING)

    # Create a concurrent batch update task
    update_task = context_manager.batch_update_contexts(app=app, file_paths=files, concurrency=5, worker_id=worker_id)

    # Track progress
    total_files = len(files)

    # Get results
    try:
        results = await update_task
        successful = sum(1 for r in results if r is not None)
        failed = sum(1 for r in results if r is None)

        if successful == total_files:
            app.ui.print_text(f"Successfully updated context for all {total_files} files", PrintType.SUCCESS)
        else:
            app.ui.print_text(f"Updated {successful} files successfully, {failed} files failed", PrintType.WARNING)
    except Exception as e:
        app.ui.print_text(f"Error updating contexts: {str(e)}", PrintType.ERROR)


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
        app.ui.print_text(f"File not found in project context: {file_path}", PrintType.ERROR)
        return

    try:
        # Get the context file path to delete it
        context_file_path = context_manager.get_context_path(file_path)

        # Remove from the index
        if "files" in context_manager.index and file_path in context_manager.index["files"]:
            del context_manager.index["files"][file_path]
            context_manager.save_index()

        # Delete the context file if it exists
        if os.path.exists(context_file_path):
            os.remove(context_file_path)

        app.ui.print_text(f"Successfully removed {file_path} from project context", PrintType.SUCCESS)
    except Exception as e:
        app.ui.print_text(f"Error removing {file_path} from project context: {str(e)}", PrintType.ERROR)
