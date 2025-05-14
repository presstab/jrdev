"""
Thread management commands for message threads

JrDev supports multiple conversation threads, each with isolated context and message history.
This is useful when working on different tasks or projects simultaneously.

Commands:
- /thread new [NAME]: Create a new thread (optionally with a custom name)
- /thread list: List all available threads
- /thread switch THREAD_ID: Switch to a different thread
- /thread info: Show information about the current thread
- /thread view [COUNT]: View conversation history in the current thread (default: 10)

For more details, see the docs/threads.md documentation.
"""

import argparse
import re
from typing import Any, List

from jrdev.commands.help import format_command_with_args_plain
from jrdev.ui.ui import PrintType, show_conversation


async def handle_thread(app: Any, args: List[str], worker_id: str) -> None:
    """Handle the /thread command for creating and managing message threads.

    Args:
        app: The application instance
        args: Command line arguments
    """
    # Create parser with enhanced descriptions
    parser = argparse.ArgumentParser(
        prog="/thread",
        description="Manage isolated conversation contexts",
        epilog=f"Examples:\n  {format_command_with_args_plain('/thread new', 'feature/auth')}\n  {format_command_with_args_plain('/thread switch', '3')}",
        exit_on_error=False
    )

    subparsers = parser.add_subparsers(dest="subcommand", title="Available subcommands")

    # New thread command
    new_parser = subparsers.add_parser(
        "new",
        help="Create new conversation thread",
        description="Create new isolated conversation context",
        epilog=f"Example: {format_command_with_args_plain('/thread new', 'my_feature')}"
    )
    new_parser.add_argument(
        "name",
        type=str,
        nargs="?",
        help="Optional name (3-20 chars, a-z0-9_-)"
    )

    # List threads command
    list_parser = subparsers.add_parser(
        "list",
        help="List all threads",
        description="Display available conversation threads",
        epilog=f"Example: {format_command_with_args_plain('/thread list')}"
    )

    # Switch thread command - Enhanced version
    switch_parser = subparsers.add_parser(
        "switch",
        help="Change active conversation context",
        description="Switch Between Conversation Contexts",
        epilog=f"Example: {format_command_with_args_plain('/thread switch NewThemeChat')}"
    )
    switch_parser.add_argument(
        "thread_id",
        type=str,
        nargs="?",
        default=None,
        help="Target thread ID (use '/thread list' to see available IDs)"
    )

    # Show thread info command
    info_parser = subparsers.add_parser(
        "info",
        help="Current thread details",
        description="Show current thread statistics",
        epilog=f"Example: {format_command_with_args_plain('/thread info')}"
    )

    # View conversation command
    view_parser = subparsers.add_parser(
        "view",
        help="Display message history",
        description="Show conversation history",
        epilog=f"Example: {format_command_with_args_plain('/thread view', '15')}"
    )
    view_parser.add_argument(
        "count",
        type=int,
        nargs="?",
        default=10,
        help="Number of messages to display (default: 10)"
    )

    try:
        # Special case for "-h" or "--help" in any position in the command
        if any(arg in ["-h", "--help"] for arg in args[1:]):
            # Display the appropriate help based on the args
            if len(args) == 2 and args[1] in ["-h", "--help"]:
                # Help for the main command
                parser.print_help()
                return
            elif len(args) >= 3 and args[2] in ["-h", "--help"]:
                # Help for specific subcommand
                sub_cmd = args[1]
                if sub_cmd in subparsers.choices:
                    subparsers.choices[sub_cmd].print_help()
                else:
                    parser.print_help()
                return
            
        # Parse arguments
        try:
            parsed_args = parser.parse_args(args[1:])
        except argparse.ArgumentError:
            # If argument parsing fails, show general help
            parser.print_help()
            return

        # Handle subcommands
        if parsed_args.subcommand == "new":
            await _handle_new_thread(app, parsed_args)
        elif parsed_args.subcommand == "list":
            await _handle_list_threads(app)
        elif parsed_args.subcommand == "switch":
            if parsed_args.thread_id is None:
                app.ui.print_text("Error: must specify a thread_id", PrintType.ERROR)
                switch_parser.print_help()  # Show specific help for switch command
                return
            await _handle_switch_thread(app, parsed_args)
        elif parsed_args.subcommand == "info":
            await _handle_thread_info(app)
        elif parsed_args.subcommand == "view":
            await _handle_view_conversation(app, parsed_args)
        else:
            app.ui.print_text("Error: Missing subcommand", PrintType.ERROR)
            app.ui.print_text("Available Thread Subcommands:", PrintType.HEADER)

            # Display formatted subcommand help
            subcommands = [
                ("new", "[name]", "Create new conversation thread", "thread new feature/login"),
                ("list", "", "List all available threads", "thread list"),
                ("switch", "<id>", "Change active thread", "thread switch 2"),
                ("info", "", "Show current thread details", "thread info"),
                ("view", "[count]", "Display message history", "thread view 5")
            ]

            for cmd, cmd_args, desc, example in subcommands:
                app.ui.print_text(
                    f"  {format_command_with_args_plain(f'/thread {cmd}', cmd_args)}",
                    PrintType.COMMAND,
                    end=""
                )
                app.ui.print_text(f" - {desc}")
                app.ui.print_text(f"    Example: {example}\n")

    except Exception as e:
        app.ui.print_text(f"Error: {str(e)}", PrintType.ERROR)
        app.ui.print_text("Thread Command Usage:", PrintType.HEADER)

        # Subcommand help sections
        sections = [
            ("Create New Thread", format_command_with_args_plain("/thread new", "[name]"),
             "Start fresh conversation with clean history\nExample: /thread new bugfix_123"),

            ("List Threads", format_command_with_args_plain("/thread list"),
             "Show all available conversation contexts\nExample: /thread list"),

            ("Switch Threads", format_command_with_args_plain("/thread switch", "<id>"),
             "Change active conversation context\nExample: /thread switch 2"),

            ("Thread Info", format_command_with_args_plain("/thread info"),
             "Show current thread statistics\nExample: /thread info"),

            ("View History", format_command_with_args_plain("/thread view", "[count]"),
             "Display message history (default 10)\nExample: /thread view 5")
        ]

        for header, cmd, desc in sections:
            app.ui.print_text(f"{header}:", PrintType.HEADER)
            app.ui.print_text(f"  {cmd}", PrintType.COMMAND)
            app.ui.print_text(f"  {desc}\n")

async def _handle_new_thread(app: Any, args: argparse.Namespace) -> None:
    """Create a new message thread
    
    Args:
        app: The application instance
        args: Parsed arguments
        
    Raises:
        ValueError: If the thread name format is invalid
    """
    # Add validation for thread name format
    if args.name and not re.match(r"^[\w-]{3,20}$", args.name):
        raise ValueError("Invalid thread name - use 3-20 alphanumerics")
    
    # Create the thread
    thread_id = app.create_thread("")
    
    # Switch to the new thread
    app.switch_thread(thread_id)
    
    app.ui.print_text(f"Created and switched to new thread: {thread_id}", PrintType.SUCCESS)

    # notify ui of thread change
    app.ui.chat_thread_update(thread_id)


async def _handle_list_threads(app: Any) -> None:
    """List all message threads
    
    Args:
        app: The application instance
    """
    threads = app.state.threads
    active_thread = app.state.active_thread
    
    app.ui.print_text("Message Threads:", PrintType.HEADER)
    
    for thread_id, thread in threads.items():
        message_count = len(thread.messages)
        context_count = len(thread.context)
        active_marker = "* " if thread_id == active_thread else "  "
        
        # Format the thread info
        app.ui.print_text(
            f"{active_marker}{thread_id} - {message_count} messages, {context_count} context files", 
            PrintType.INFO if thread_id == active_thread else PrintType.INFO
        )


# Updated switch handler with enhanced output
async def _handle_switch_thread(app: Any, args: argparse.Namespace) -> None:
    """Switch to a different message thread with visual feedback"""
    thread_id = getattr(args, 'thread_id', None)
    if not thread_id:
        app.ui.print_text("Error: Must specify thread ID", PrintType.ERROR)
        return

    app.ui.print_text("Switching Context...", PrintType.HEADER)

    # Validate thread existence
    if thread_id not in app.state.threads:
        app.ui.print_text(
            f"Thread {thread_id} not found",
            PrintType.ERROR
        )
        app.ui.print_text(
            "Use /thread list to see available threads",
            PrintType.INFO
        )
        return

    # Perform switch with visual feedback
    previous_thread = app.state.active_thread
    if app.switch_thread(thread_id):
        new_thread = app.state.get_current_thread()

        # Success message with thread stats
        app.ui.print_text(
            f"Successfully switched to thread {thread_id}",
            PrintType.SUCCESS
        )
        app.ui.print_text(
            f"Thread Stats:\n"
            f"  Messages: {len(new_thread.messages)} | "
            f"Context Files: {len(new_thread.context)}\n"
            f"Embedded Files: {len(new_thread.embedded_files)}",
            PrintType.INFO
        )

        # notify ui of thread change
        app.ui.chat_thread_update(new_thread.thread_id)
    else:
        app.ui.print_text(
            f"Failed to switch to thread {thread_id}",
            PrintType.ERROR
        )
        app.switch_thread(previous_thread)  # Revert to previous thread

        # notify ui of thread change
        app.ui.chat_thread_update(previous_thread)

async def _handle_thread_info(app: Any) -> None:
    """Show information about the current thread
    
    Args:
        app: The application instance
    """
    thread_id = app.state.active_thread
    thread = app.state.get_current_thread()
    
    # Get thread stats
    message_count = len(thread.messages)
    context_count = len(thread.context)
    files_count = len(thread.embedded_files)
    
    # Get message roles breakdown
    user_messages = sum(1 for msg in thread.messages if msg.get("role") == "user")
    assistant_messages = sum(1 for msg in thread.messages if msg.get("role") == "assistant")
    system_messages = sum(1 for msg in thread.messages if msg.get("role") == "system")
    
    # Show thread information
    app.ui.print_text(f"Thread ID: {thread_id}", PrintType.HEADER)
    app.ui.print_text(f"Total messages: {message_count}", PrintType.INFO)
    app.ui.print_text(f"  User messages: {user_messages}", PrintType.INFO)
    app.ui.print_text(f"  Assistant messages: {assistant_messages}", PrintType.INFO)
    app.ui.print_text(f"  System messages: {system_messages}", PrintType.INFO)
    app.ui.print_text(f"Context files: {context_count}", PrintType.INFO)
    app.ui.print_text(f"Files referenced: {files_count}", PrintType.INFO)
    
    # Show context files if any
    if context_count > 0:
        app.ui.print_text("Context files:", PrintType.INFO)
        for ctx_file in thread.context:
            app.ui.print_text(f"  {ctx_file}", PrintType.INFO)
            
    # Show conversation preview
    if message_count > 0:
        show_conversation(app, max_messages=5)
        
        
async def _handle_view_conversation(app: Any, args: argparse.Namespace) -> None:
    """View the conversation in the current thread
    
    Args:
        app: The application instance
        args: Parsed arguments
    """
    # Get the max message count from args (default is handled by argparse)
    max_messages = args.count
    
    # Show the conversation
    show_conversation(app, max_messages=max_messages)
