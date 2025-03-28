#!/usr/bin/env python3

"""
Project context command implementation for the JrDev terminal.
"""

import os
from typing import List

from jrdev.ui.ui import terminal_print, PrintType


async def handle_projectcontext(terminal, args):
    """
    Handle the /projectcontext command for managing project context.
    
    Commands:
        /projectcontext on|off - Toggle using project context in requests
        /projectcontext status - Show current status of project context
        /projectcontext list - List all tracked files in context
        /projectcontext view <filepath> - View context for a specific file
        /projectcontext refresh <filepath> - Refresh context for a specific file
    
    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments 
    """
    if len(args) < 2:
        _show_usage()
        return

    command = args[1].lower()
    
    if command == "on":
        terminal.use_project_context = True
        terminal_print("Project context is now ON", PrintType.SUCCESS)
    
    elif command == "off":
        terminal.use_project_context = False
        terminal_print("Project context is now OFF", PrintType.SUCCESS)
    
    elif command == "status":
        await _show_status(terminal)
    
    elif command == "list":
        await _list_context_files(terminal)
    
    elif command == "view" and len(args) > 2:
        await _view_file_context(terminal, args[2])
    
    elif command == "refresh" and len(args) > 2:
        await _refresh_file_context(terminal, args[2])
    
    else:
        _show_usage()


def _show_usage():
    """
    Show usage information for the projectcontext command.
    """
    terminal_print("Project Context Command Usage:", PrintType.HEADER)
    terminal_print("/projectcontext on|off - Toggle using project context in requests", PrintType.INFO)
    terminal_print("/projectcontext status - Show current status of project context", PrintType.INFO)
    terminal_print("/projectcontext list - List all tracked files in context", PrintType.INFO)
    terminal_print("/projectcontext view <filepath> - View context for a specific file", PrintType.INFO)
    terminal_print("/projectcontext refresh <filepath> - Refresh context for a specific file", PrintType.INFO)


async def _show_status(terminal):
    """
    Show the current status of the project context system.
    
    Args:
        terminal: The JrDevTerminal instance
    """
    context_manager = terminal.context_manager
    file_count = len(context_manager.index.get("files", {}))
    outdated_files = context_manager.get_outdated_files()
    
    terminal_print("Project Context Status:", PrintType.HEADER)
    terminal_print(f"Context enabled: {terminal.use_project_context}", PrintType.INFO)
    terminal_print(f"Files tracked: {file_count}", PrintType.INFO)
    terminal_print(f"Outdated files: {len(outdated_files)}", PrintType.INFO)
    
    if outdated_files:
        terminal_print("\nOutdated files that need refreshing:", PrintType.WARNING)
        for file in outdated_files[:10]:  # Show at most 10 files
            terminal_print(f"- {file}", PrintType.INFO)
        
        if len(outdated_files) > 10:
            terminal_print(f"... and {len(outdated_files) - 10} more", PrintType.INFO)


async def _list_context_files(terminal):
    """
    List all files tracked in the context system.
    
    Args:
        terminal: The JrDevTerminal instance
    """
    context_manager = terminal.context_manager
    files = list(context_manager.index.get("files", {}).keys())
    
    if not files:
        terminal_print("No files in context", PrintType.WARNING)
        return
    
    terminal_print(f"Tracked Files ({len(files)}):", PrintType.HEADER)
    
    # Group files by directory for better organization
    dir_to_files = {}
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


async def _view_file_context(terminal, file_path):
    """
    View the context for a specific file.
    
    Args:
        terminal: The JrDevTerminal instance
        file_path: Path to the file to view context for
    """
    context_manager = terminal.context_manager
    context = context_manager._read_context_file(file_path)
    
    if not context:
        terminal_print(f"No context found for {file_path}", PrintType.WARNING)
        return
    
    terminal_print(f"Context for {file_path}:", PrintType.HEADER)
    terminal_print(context, PrintType.INFO)


async def _refresh_file_context(terminal, file_path):
    """
    Refresh the context for a specific file.
    
    Args:
        terminal: The JrDevTerminal instance
        file_path: Path to the file to refresh context for
    """
    if not os.path.exists(file_path):
        terminal_print(f"File not found: {file_path}", PrintType.ERROR)
        return
    
    terminal_print(f"Refreshing context for {file_path}...", PrintType.PROCESSING)
    
    # Use the context manager to regenerate the context
    analysis = await terminal.context_manager.generate_context(file_path, terminal)
    
    if analysis:
        terminal_print(f"Successfully refreshed context for {file_path}", PrintType.SUCCESS)
    else:
        terminal_print(f"Failed to refresh context for {file_path}", PrintType.ERROR)