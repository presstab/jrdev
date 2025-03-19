#!/usr/bin/env python3

"""
Help command implementation for the JrDev terminal.
"""

from jrdev.ui import terminal_print, PrintType, COLORS, FORMAT_MAP


async def handle_help(terminal, args):
    """
    Handle the /help command to display available commands categorized.
    """
    terminal_print("Available commands:", print_type=PrintType.HEADER)

    # Basic commands
    terminal_print("Basic:", print_type=PrintType.SUBHEADER)
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
        f"  /model <model_name>",
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
        f"  /cost",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Display session costs")

    # Use AI commands
    terminal_print("Use AI:", print_type=PrintType.SUBHEADER)
    terminal_print(
        f"  /init",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Index important project files and familiarize LLM with project")

    # Add experimental tag to code command with green color
    exp_tag = f"{COLORS['BRIGHT_GREEN']}(WIP){FORMAT_MAP[PrintType.COMMAND]}"
    terminal_print(
        f"  /code <message> {exp_tag}",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Send coding task to LLM. LLM will request needed files and save an updated version.")

    terminal_print(
        f"  /asyncsend [filepath] <prompt>",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Send message in background and save to a file")

    # Add default tag to chat command with yellow color
    default_tag = f"{COLORS['BRIGHT_YELLOW']}(default){FORMAT_MAP[PrintType.COMMAND]}"
    terminal_print(
        f"  /chat <message> {default_tag}",
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
        f"  /cancel <task_id>|all",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Cancel background tasks")

    # Context Control commands
    terminal_print("Context Control:", print_type=PrintType.SUBHEADER)
    terminal_print(
        f"  /addcontext <file_path or pattern>",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - Add file(s) to the LLM context window")
    terminal_print(
        f"  /viewcontext [number]",
        print_type=PrintType.COMMAND,
        end=""
    )
    terminal_print(f" - View the LLM context window content")
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
