#!/usr/bin/env python3

"""
ViewContext command implementation for the JrDev terminal.
"""
import os

from jrdev.ui.ui import terminal_print, PrintType


async def handle_viewcontext(terminal, args):
    """
    Handle the /viewcontext command to view the content in the LLM context window.

    Args:
        terminal: The JrDevTerminal instance
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
    if not terminal.context:
        terminal_print("No context files have been added yet. Use /addcontext <file_path> to add files.", PrintType.INFO)
        return
    
    # If a specific file was requested
    if file_num is not None:
        if file_num < 0 or file_num >= len(terminal.context):
            terminal_print(f"Invalid file number. Please use a number between 1 and {len(terminal.context)}.", PrintType.ERROR)
            return
            
        ctx = terminal.context[file_num]
        terminal_print(f"Context File {file_num+1}: {ctx['name']}", PrintType.HEADER)
        terminal_print(ctx['content'], PrintType.INFO)
        return
        
    # Otherwise show a summary of all files
    terminal_print("Current context content:", PrintType.HEADER)
    terminal_print(f"Total files in context: {len(terminal.context)}", PrintType.INFO)
    
    # Show a summary of files in the context
    terminal_print("Files in context:", PrintType.INFO)
    for i, ctx in enumerate(terminal.context):
        # Calculate a preview of the content (first 50 chars)
        preview = ctx['content'][:50].replace('\n', ' ') + ('...' if len(ctx['content']) > 50 else '')
        terminal_print(f"  {i+1}. {ctx['name']} - {preview}", PrintType.COMMAND)
    
    terminal_print("\nUse '/viewcontext <number>' to view the full content of a specific file.", PrintType.INFO)    
    terminal_print("Use /addcontext <file_path> to add more files to the context.", PrintType.INFO)
    terminal_print("Use /clearcontext to clear all context files.", PrintType.INFO)