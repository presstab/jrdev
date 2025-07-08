#!/usr/bin/env python3

"""
Help command implementation for the JrDev application.
"""

from typing import Any, List

from jrdev import __version__
from jrdev.ui.ui import COLORS, FORMAT_MAP, PrintType


def format_command_with_args(command, args=None):
    """
    Format a command with grey arguments that are not bold.

    Args:
        command: The base command (e.g., "/help")
        args: Optional arguments to add in grey (e.g., "<message>")

    Returns:
        Formatted command string with grey arguments
    """
    if args:
        # Format the arguments in grey and remove bold formatting
        grey_args = f"{COLORS['RESET']}{COLORS['BRIGHT_BLACK']}{args}"
        return f"{command} {grey_args}"
    return command


def format_command_with_args_plain(command, args=None):
    """
    Format a command with arguments without any color formatting.

    Args:
        command: The base command (e.g., "/help")
        args: Optional arguments to add (e.g., "<message>")

    Returns:
        Plain formatted command string with arguments
    """
    if args:
        return f"{command} {args}"
    return command


async def handle_help(app: Any, args: List[str], _worker_id: str):
    """
    Displays a categorized list of all available commands and their functions.

    This command provides a comprehensive overview of the application's capabilities,
    grouped by category for easy navigation.

    Usage:
      /help
    """
    if app.ui.ui_name == "textual":
        return await handle_help_plain(app, args)

    # Version
    app.ui.print_text(f"{COLORS['BRIGHT_WHITE']}JrDev v{__version__}:{COLORS['RESET']}", print_type=None)

    # Basic commands
    app.ui.print_text(
        f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Basic:{COLORS['RESET']}", print_type=None
    )

    # Format each command line as a single string
    cmd_format = FORMAT_MAP[PrintType.COMMAND]
    reset = COLORS["RESET"]

    app.ui.print_text(f"  {cmd_format}/exit{reset} - Exit the application", print_type=None)
    app.ui.print_text(f"  {cmd_format}/help{reset} - Show this help message", print_type=None)
    app.ui.print_text(f"  {cmd_format}/cost{reset} - Display session costs", print_type=None)
    app.ui.print_text(f"  {cmd_format}/keys{reset} - Manage API keys", print_type=None)

    # Use AI commands
    app.ui.print_text(
        f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Use AI:{COLORS['RESET']}", print_type=None
    )

    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/model', '<list|set|remove|add|edit> [args]')}{reset} "
        "- Manage and add models (/model add|edit <name> <provider> <is_think> <input_cost> <output_cost> "
        "<context_window>)",
        print_type=None,
    )
    app.ui.print_text(f"  {cmd_format}/models{reset} - List all available models", print_type=None)
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/modelprofile', '<list|get|set|default|showdefault>')}"
        f"{reset} - Manage model profiles for different task types",
        print_type=None,
    )
    app.ui.print_text(
        f"  {cmd_format}/init{reset} - Index important project files and familiarize LLM with project", print_type=None
    )
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/routeragent', '<clear|set-max-iter> <number>')}{reset} - "
        "Configure the router agent",
        print_type=None,
    )

    # Add experimental tag to code command with green color
    exp_tag = f"{COLORS['RESET']}{COLORS['BRIGHT_GREEN']}(WIP){FORMAT_MAP[PrintType.COMMAND]}"
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/code', '<message>')} {exp_tag}{reset} - Send coding "
        "task to LLM. LLM will read and edit the code.",
        print_type=None,
    )

    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/asyncsend', '[filepath] <prompt>')}{reset} - Send "
        "message in background and save to a file",
        print_type=None,
    )

    # Add default tag to chat command with yellow color
    default_tag = f"{COLORS['RESET']}{COLORS['BRIGHT_YELLOW']}(default){FORMAT_MAP[PrintType.COMMAND]}"
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/chat', '<message>')} {default_tag}{reset} - Chat with"
        " the AI about your project (using no command will default here)",
        print_type=None,
    )

    app.ui.print_text(f"  {cmd_format}/tasks{reset} - List active background tasks", print_type=None)
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/cancel', '<task_id>|all')}{reset} - Cancel background" " tasks",
        print_type=None,
    )

    # Thread and Context Control commands
    app.ui.print_text(
        f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Message Threads & Context Control:"
        f"{COLORS['RESET']}",
        print_type=None,
    )

    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/thread', '<new|list|switch|info>')}{reset} - Manage "
        "separate message threads with isolated context",
        print_type=None,
    )
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/addcontext', '<file_path or pattern>')}{reset} - Add "
        "file(s) to the LLM context window",
        print_type=None,
    )
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/viewcontext', '[number]')}{reset} - View the LLM "
        "context window content",
        print_type=None,
    )
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/projectcontext', '<argument|help>')}{reset} - Manage "
        "project context for efficient LLM interactions",
        print_type=None,
    )
    app.ui.print_text(f"  {cmd_format}/clearcontext{reset} - Clear context and conversation history", print_type=None)
    app.ui.print_text(
        f"  {cmd_format}/compact{reset} - Compact conversation history to two essential messages", print_type=None
    )
    app.ui.print_text(f"  {cmd_format}/stateinfo{reset} - Display application state information", print_type=None)

    # Git Operations
    app.ui.print_text(
        f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Git Operations:{COLORS['RESET']}",
        print_type=None,
    )

    app.ui.print_text(f"  {cmd_format}/git{reset} - Git-related commands (use '/git' for details)", print_type=None)
    app.ui.print_text(
        f"  {cmd_format}{format_command_with_args('/git pr', '<command>')}{reset} - PR-related commands",
        print_type=None,
    )

    # Roadmap section
    app.ui.print_text(
        f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Roadmap (Coming Soon):{COLORS['RESET']}",
        print_type=None,
    )

    # Define baby blue color for roadmap commands
    baby_blue = f"{COLORS['RESET']}{COLORS['BRIGHT_CYAN']}{COLORS['BOLD']}"

    app.ui.print_text(
        f"  {baby_blue}/tasklist{COLORS['RESET']} - Create task lists for an agent to work on in the background",
        print_type=None,
    )
    app.ui.print_text(
        f"  {baby_blue}/agent{COLORS['RESET']} - Create an AI agent that specializes in certain tasks", print_type=None
    )
    app.ui.print_text(
        f"  {baby_blue}/server{COLORS['RESET']} - Launch API server to access our features however you prefer",
        print_type=None,
    )


async def handle_help_plain(app: Any, _args: List[str]):
    """
    Handle the /help command to display available commands categorized without color formatting.
    """
    app.ui.print_text(f"JrDev v{__version__}")
    app.ui.print_text("")

    # Basic commands
    app.ui.print_text("Basic:", print_type=None)

    app.ui.print_text("  /exit - Exit the application", print_type=None)
    app.ui.print_text("  /help - Show this help message", print_type=None)
    app.ui.print_text("  /cost - Display session costs", print_type=None)
    app.ui.print_text("  /keys - Manage API keys", print_type=None)

    # Use AI commands
    app.ui.print_text("Use AI:", print_type=None)

    app.ui.print_text(
        "  /model <list|set|remove|add|edit> [args] - Manage and add models (/model add|edit <name> <provider> "
        "<is_think> <input_cost> <output_cost> <context_window>)",
        print_type=None,
    )
    app.ui.print_text("  /models - List all available models", print_type=None)
    app.ui.print_text(
        "  /modelprofile <list|get|set|default|showdefault> - Manage model profiles for different task types",
        print_type=None,
    )
    app.ui.print_text("  /init - Index important project files and familiarize LLM with project", print_type=None)
    app.ui.print_text("  /routeragent <set-max-iter> <number> - Configure the router agent", print_type=None)
    app.ui.print_text(
        "  /code <message> (WIP) - Send coding task to LLM. LLM will read and edit the code.", print_type=None
    )
    app.ui.print_text(
        "  /asyncsend [filepath] <prompt> - Send message in background and save to a file", print_type=None
    )
    app.ui.print_text(
        "  /chat <message> (default) - Chat with the AI about your project (using no command will default here)",
        print_type=None,
    )
    app.ui.print_text("  /tasks - List active background tasks", print_type=None)
    app.ui.print_text("  /cancel <task_id>|all - Cancel background tasks", print_type=None)

    # Thread and Context Control commands
    app.ui.print_text("Message Threads & Context Control:", print_type=None)

    app.ui.print_text(
        "  /thread <new|list|switch|info> - Manage separate message threads with isolated context", print_type=None
    )
    app.ui.print_text("  /addcontext <file_path or pattern> - Add file(s) to the LLM context window", print_type=None)
    app.ui.print_text("  /viewcontext [number] - View the LLM context window content", print_type=None)
    app.ui.print_text(
        "  /projectcontext <argument|help> - Manage project context for efficient LLM interactions", print_type=None
    )
    app.ui.print_text("  /clearcontext - Clear context and conversation history", print_type=None)
    app.ui.print_text(
        "  /compact - Compact conversation history into a concise summary to reduce token use", print_type=None
    )
    app.ui.print_text("  /stateinfo - Display application state information", print_type=None)

    # Git Operations
    app.ui.print_text("Git Operations:", print_type=None)

    app.ui.print_text("  /git - Git-related commands (use '/git' for details)", print_type=None)
    app.ui.print_text("  /git pr <command> - PR-related commands", print_type=None)

    # Roadmap section
    app.ui.print_text("Roadmap (Coming Soon):", print_type=None)

    app.ui.print_text("  /tasklist - Create task lists for an agent to work on in the background", print_type=None)
    app.ui.print_text("  /agent - Create an AI agent that specializes in certain tasks", print_type=None)
    app.ui.print_text("  /server - Launch API server to access our features however you prefer", print_type=None)
