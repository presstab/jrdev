#!/usr/bin/env python3

"""
Help command implementation for the JrDev terminal.
"""

from jrdev.ui.ui import terminal_print, PrintType, COLORS, FORMAT_MAP


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


async def handle_help(terminal, args):
    """
    Handle the /help command to display available commands categorized.
    """
    # Basic commands
    terminal_print(f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Basic:{COLORS['RESET']}", print_type=None)
    terminal_print(
        f"  /exit",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Exit the terminal")
    terminal_print(
        f"  /help",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Show this help message")
    terminal_print(
        f"  /cost",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Display session costs")

    # Use AI commands
    terminal_print(f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Use AI:{COLORS['RESET']}", print_type=None)
    terminal_print(
        f"  {format_command_with_args('/model', '<model_name>')}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Change model")
    terminal_print(
        f"  /models",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - List all available models")
    terminal_print(
        f"  /init",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Index important project files and familiarize LLM with project")

    # Add experimental tag to code command with green color
    exp_tag = f"{COLORS['RESET']}{COLORS['BRIGHT_GREEN']}(WIP){FORMAT_MAP[PrintType.COMMAND]}"
    terminal_print(
        f"  {format_command_with_args('/code', '<message>')} {exp_tag}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Send coding task to LLM. LLM will read and edit the code.")

    terminal_print(
        f"  {format_command_with_args('/asyncsend', '[filepath] <prompt>')}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Send message in background and save to a file")

    # Add default tag to chat command with yellow color
    default_tag = f"{COLORS['RESET']}{COLORS['BRIGHT_YELLOW']}(default){FORMAT_MAP[PrintType.COMMAND]}"
    terminal_print(
        f"  {format_command_with_args('/chat', '<message>')} {default_tag}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Chat with the AI about your project (using no command will default here)")

    terminal_print(
        f"  /tasks",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - List active background tasks")

    terminal_print(
        f"  {format_command_with_args('/cancel', '<task_id>|all')}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Cancel background tasks")

    # Context Control commands
    terminal_print(f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Context Control:{COLORS['RESET']}", print_type=None)
    terminal_print(
        f"  {format_command_with_args('/addcontext', '<file_path or pattern>')}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Add file(s) to the LLM context window")
    terminal_print(
        f"  {format_command_with_args('/viewcontext', '[number]')}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - View the LLM context window content")
    terminal_print(
        f"  {format_command_with_args('/projectcontext', '<argument|help>')}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Manage project context for efficient LLM interactions")
    terminal_print(
        f"  /clearcontext",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Clear context and conversation history")
    terminal_print(
        f"  /clearmessages",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Clear message history for all models")
    terminal_print(
        f"  /stateinfo",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Display terminal state information")
    
    # Git Operations
    terminal_print(f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Git Operations:{COLORS['RESET']}", print_type=None)
    terminal_print(
        f"  /git",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Git-related commands (use '/git' for details)")
    terminal_print(
        f"  {format_command_with_args('/git pr', '<command>')}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - PR-related commands")
    
    # Roadmap section
    terminal_print(f"{COLORS['BRIGHT_WHITE']}{COLORS['BOLD']}{COLORS['UNDERLINE']}Roadmap (Coming Soon):{COLORS['RESET']}", print_type=None)
    
    # Define baby blue color for roadmap commands
    baby_blue = f"{COLORS['RESET']}{COLORS['BRIGHT_CYAN']}{COLORS['BOLD']}"
    
    terminal_print(
        f"  {baby_blue}/tasklist{COLORS['RESET']}",
        end=""
    )
    terminal_print(f" - Create task lists for an agent to work on in the background")
    
    terminal_print(
        f"  {baby_blue}/agent{COLORS['RESET']}",
        end=""
    )
    terminal_print(f" - Create an AI agent that specializes in certain tasks")
    
    terminal_print(
        f"  {baby_blue}/server{COLORS['RESET']}",
        end=""
    )
    terminal_print(f" - Launch API server to access our features however you prefer")
