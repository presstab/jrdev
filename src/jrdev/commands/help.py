#!/usr/bin/env python3

"""
Help command implementation for the JrDev terminal.
"""

from jrdev.ui import terminal_print, PrintType


async def handle_help(terminal, args):
    """
    Handle the /help command to display available commands.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal_print("Available commands:", print_type=PrintType.HEADER)
    terminal_print("  /exit - Exit the terminal", print_type=PrintType.COMMAND)
    terminal_print("  /model <model_name> - Change the model", print_type=PrintType.COMMAND)
    terminal_print("  /models - List all available models", print_type=PrintType.COMMAND)
    terminal_print("  /addcontext <file_path or pattern> - Add file(s) to the LLM context window", print_type=PrintType.COMMAND)
    terminal_print("  /viewcontext [number] - View the content in the LLM context window", print_type=PrintType.COMMAND)
    terminal_print("  /clearcontext - Clear context files and conversation history", print_type=PrintType.COMMAND)
    terminal_print("  /clearmessages - Clear message history for all models", print_type=PrintType.COMMAND)
    terminal_print("  /process on|off - Enable or disable automatic file processing", print_type=PrintType.COMMAND)
    terminal_print("  /asyncsend [filepath] <prompt> - Send message in background and optionally save to a file", print_type=PrintType.COMMAND)
    terminal_print("  /tasks - List all active background tasks", print_type=PrintType.COMMAND)
    terminal_print("  /cancel <task_id>|all - Cancel background task(s)", print_type=PrintType.COMMAND)
    terminal_print(
        "  /init [filename] - Generate file tree, analyze files, and create project overview",
        print_type=PrintType.COMMAND
    )
    terminal_print("  /stateinfo - Display current terminal state information", print_type=PrintType.COMMAND)
    terminal_print("  /cost - Display session cost breakdown by model", print_type=PrintType.COMMAND)
    terminal_print("  /help - Show this help message", print_type=PrintType.COMMAND)
