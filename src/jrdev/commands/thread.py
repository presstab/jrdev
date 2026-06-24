"""Thread management commands for message threads

JrDev supports multiple conversation threads, each with isolated context and message history.
This is useful when working on different tasks or projects simultaneously.

Commands:
- /thread new [NAME]: Create a new thread (optionally with a custom name)
- /thread list: List all available threads
- /thread switch THREAD_ID: Switch to a different thread
- /thread rename THREAD_ID NAME: Rename an existing thread
- /thread name-all: Generate names for unnamed threads
- /thread info: Show information about the current thread
- /thread view [COUNT]: View conversation history in the current thread (default: 10)
- /thread delete THREAD_ID: Delete an existing thread

Additional toggle:
- /thread websearch on|off: Enable or disable per-thread web search mode used by chat input

For more details, see the docs/threads.md documentation.
"""

import argparse
import re
from typing import Any, Dict, List, Optional

from jrdev.commands.help import format_command_with_args_plain
from jrdev.messages.thread import MessageThread, USER_INPUT_PREFIX  # For type hinting
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.llm_requests import generate_llm_response
from jrdev.services.message_service import THREAD_NAME_PATTERN, _sanitize_thread_name
from jrdev.ui.ui import PrintType, show_conversation


# pylint: disable=too-many-locals, too-many-branches, too-many-statements
async def handle_thread(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Manages isolated conversation threads, each with its own history and context.

    Threads are useful for working on different tasks or features simultaneously
    without mixing conversations.

    Usage:
      /thread <subcommand> [arguments]

    Subcommands:
      new [name]              - Creates and switches to a new thread.
      list                    - Lists all available threads.
      switch <thread_id>      - Switches to an existing thread.
      rename <thread_id> <name> - Renames an existing thread.
      name-all                - Uses the low_cost_search model to name unnamed threads.
      info                    - Shows information about the current thread.
      view [count]            - Views conversation history (default: 10 messages).
      delete <thread_id>      - Deletes an existing thread.
    """
    parser = argparse.ArgumentParser(
        prog="/thread",
        description="Manage isolated conversation contexts",
        epilog=(
            f"Examples:\n  {format_command_with_args_plain('/thread new', 'feature/auth')}\n  "
            f"{format_command_with_args_plain('/thread switch', '3')}\n  "
            f"{format_command_with_args_plain('/thread rename', 'thread-abc new-feature-name')}"
        ),
        exit_on_error=False,
    )

    subparsers = parser.add_subparsers(dest="subcommand", title="Available subcommands")

    # New thread command
    new_parser = subparsers.add_parser(
        "new",
        help="Create new conversation thread",
        description="Create new isolated conversation context",
        epilog=f"Example: {format_command_with_args_plain('/thread new', 'my_feature')}",
    )
    help_str = "Optional name (3-20 chars, a-z0-9_- )"
    new_parser.add_argument("name", type=str, nargs=argparse.REMAINDER, help=help_str)

    # List threads command
    subparsers.add_parser(
        "list",
        help="List all threads",
        description="Display available conversation threads",
        epilog=f"Example: {format_command_with_args_plain('/thread list')}",
    )

    # Switch thread command
    switch_parser = subparsers.add_parser(
        "switch",
        help="Change active conversation context",
        description="Switch Between Conversation Contexts",
        epilog=f"Example: {format_command_with_args_plain('/thread switch', 'NewThemeChat')}",
    )
    switch_parser.add_argument(
        "thread_id",
        type=str,
        nargs="?",
        default=None,
        help="Target thread ID (use '/thread list' to see available IDs)",
    )

    # Rename thread command
    rename_parser = subparsers.add_parser(
        "rename",
        help="Rename an existing thread",
        description="Change the name of an existing conversation thread",
        epilog=f"Example: {format_command_with_args_plain('/thread rename', 'thread_abc new_name')}",
    )
    rename_parser.add_argument("thread_id", type=str, help="Unique ID of the thread to rename")
    rename_parser.add_argument(
        "name", type=str, nargs=argparse.REMAINDER, help="New name for the thread (3-20 chars, a-z0-9_- )"
    )

    # Name all unnamed threads command
    subparsers.add_parser(
        "name-all",
        help="Generate names for unnamed threads",
        description="Use the low_cost_search model to generate names for unnamed conversation threads",
        epilog=f"Example: {format_command_with_args_plain('/thread name-all')}",
    )

    # Show thread info command
    subparsers.add_parser(
        "info",
        help="Current thread details",
        description="Show current thread statistics",
        epilog=f"Example: {format_command_with_args_plain('/thread info')}",
    )

    # View conversation command
    view_parser = subparsers.add_parser(
        "view",
        help="Display message history",
        description="Show conversation history",
        epilog=f"Example: {format_command_with_args_plain('/thread view', '15')}",
    )
    view_parser.add_argument(
        "count", type=int, nargs="?", default=10, help="Number of messages to display (default: 10)"
    )

    # Delete thread command
    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete an existing thread",
        description="Remove an existing conversation thread",
        epilog=f"Example: {format_command_with_args_plain('/thread delete', 'thread_abc')}",
    )
    delete_parser.add_argument("thread_id", type=str, help="Unique ID of the thread to delete")

    # Web search toggle (per-thread)
    websearch_parser = subparsers.add_parser(
        "websearch",
        help="Toggle web search for current thread",
        description="Enable or disable per-thread web search mode",
        epilog=f"Example: {format_command_with_args_plain('/thread websearch', 'on')}",
    )
    websearch_parser.add_argument(
        "state",
        type=str,
        choices=["on", "off"],
        help="Turn web search on or off for the current thread",
    )

    try:
        if any(arg in ["-h", "--help"] for arg in args[1:]):
            if len(args) == 2 and args[1] in ["-h", "--help"]:
                parser.print_help()
                return
            if len(args) >= 3 and args[2] in ["-h", "--help"]:
                sub_cmd = args[1]
                if sub_cmd in subparsers.choices:
                    subparsers.choices[sub_cmd].print_help()
                else:
                    parser.print_help()
                return

        try:
            parsed_args = parser.parse_args(args[1:])
        except argparse.ArgumentError:
            parser.print_help()
            return

        if parsed_args.subcommand == "new":
            await _handle_new_thread(app, parsed_args)
        elif parsed_args.subcommand == "list":
            await _handle_list_threads(app)
        elif parsed_args.subcommand == "switch":
            if parsed_args.thread_id is None:
                app.ui.print_text("Error: must specify a thread_id", PrintType.ERROR)
                switch_parser.print_help()
                return
            await _handle_switch_thread(app, parsed_args)
        elif parsed_args.subcommand == "rename":
            await _handle_rename_thread(app, parsed_args)
        elif parsed_args.subcommand == "name-all":
            await _handle_name_all_threads(app, _worker_id)
        elif parsed_args.subcommand == "info":
            await _handle_thread_info(app)
        elif parsed_args.subcommand == "view":
            await _handle_view_conversation(app, parsed_args)
        elif parsed_args.subcommand == "delete":
            await _handle_delete_thread(app, parsed_args)
        elif parsed_args.subcommand == "websearch":
            await _handle_websearch_toggle(app, parsed_args)
        else:
            app.ui.print_text("Error: Missing subcommand", PrintType.ERROR)
            app.ui.print_text("Available Thread Subcommands:", PrintType.HEADER)

            subcommands = [
                ("new", "[name]", "Create new conversation thread", "thread new feature/login"),
                ("list", "", "List all available threads", "thread list"),
                ("switch", "<id>", "Change active thread", "thread switch 2"),
                ("rename", "<thread_id> <name>", "Rename an existing thread", "thread rename thread_abc new_name"),
                ("name-all", "", "Generate names for unnamed threads", "thread name-all"),
                ("info", "", "Show current thread details", "thread info"),
                ("view", "[count]", "Display message history", "thread view 5"),
                ("delete", "<thread_id>", "Delete an existing thread", "thread delete thread_abc"),
            ]

            for cmd, cmd_args, desc, example in subcommands:
                app.ui.print_text(
                    f"  {format_command_with_args_plain(f'/thread {cmd}', cmd_args)}", PrintType.COMMAND, end=""
                )
                app.ui.print_text(f" - {desc}")
                app.ui.print_text(f"    Example: {example}\n")

    except Exception as e:
        app.ui.print_text(f"Error: {str(e)}", PrintType.ERROR)
        app.ui.print_text("Thread Command Usage:", PrintType.HEADER)

        sections = [
            (
                "Create New Thread",
                format_command_with_args_plain("/thread new", "[name]"),
                "Start fresh conversation with clean history\nExample: /thread new bugfix_123",
            ),
            (
                "List Threads",
                format_command_with_args_plain("/thread list"),
                "Show all available conversation contexts\nExample: /thread list",
            ),
            (
                "Switch Threads",
                format_command_with_args_plain("/thread switch", "<id>"),
                "Change active conversation context\nExample: /thread switch 2",
            ),
            (
                "Rename Thread",
                format_command_with_args_plain("/thread rename", "<thread_id> <new_name>"),
                "Change the name of an existing thread\nExample: /thread rename my_thread_id new_feature_name",
            ),
            (
                "Name Unnamed Threads",
                format_command_with_args_plain("/thread name-all"),
                "Generate names for unnamed conversation threads\nExample: /thread name-all",
            ),
            (
                "Thread Info",
                format_command_with_args_plain("/thread info"),
                "Show current thread statistics\nExample: /thread info",
            ),
            (
                "View History",
                format_command_with_args_plain("/thread view", "[count]"),
                "Display message history (default 10)\nExample: /thread view 5",
            ),
            (
                "Delete Thread",
                format_command_with_args_plain("/thread delete", "<thread_id>"),
                "Remove an unwanted thread\nExample: /thread delete thread_abc",
            ),
            (
                "Web Search",
                format_command_with_args_plain("/thread websearch", "on|off"),
                "Enable or disable per-thread web search mode used by chat input\nExample: /thread websearch on",
            ),
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
    name = None
    if hasattr(args, "name") and args.name:
        # args.name is a list (possibly empty) due to nargs=REMAINDER
        name = " ".join(args.name).strip()
        if name and not re.match(r"^[\w\- ]{3,40}$", name):
            raise ValueError("Invalid thread name - use 3-40 alphanumerics, underscores, hyphens, or spaces")
        if not name:
            name = None

    thread_id = app.create_thread("")

    if name:
        thread = app.state.threads[thread_id]
        thread.set_name(name)

    app.switch_thread(thread_id)

    app.ui.print_text(
        f"Created and switched to new thread: {thread_id}{f' (named: {name})' if name else ''}", PrintType.SUCCESS
    )
    app.ui.chat_thread_update(thread_id)


async def _handle_list_threads(app: Any) -> None:
    """List all message threads

    Args:
        app: The application instance
    """
    threads = app.state.threads
    active_thread = app.state.active_thread
    router_thread_id = app.state.router_thread_id

    app.ui.print_text("Message Threads:", PrintType.HEADER)

    for thread_id, thread in threads.items():
        if thread_id == router_thread_id:
            continue
        message_count = len(thread.messages)
        context_count = len(thread.context)
        active_marker = "* " if thread_id == active_thread else "  "
        name_display = f" (Name: {thread.name})" if thread.name else ""

        app.ui.print_text(
            f"{active_marker}{thread_id}{name_display} - {message_count} messages, {context_count} context files",
            PrintType.INFO if thread_id == active_thread else PrintType.INFO,
        )


async def _handle_switch_thread(app: Any, args: argparse.Namespace) -> None:
    """Switch to a different message thread with visual feedback"""
    thread_id = getattr(args, "thread_id", None)
    if not thread_id:
        app.ui.print_text("Error: Must specify thread ID", PrintType.ERROR)
        return

    app.ui.print_text("Switching Context...", PrintType.HEADER)

    if thread_id not in app.state.threads:
        app.ui.print_text(f"Thread {thread_id} not found", PrintType.ERROR)
        app.ui.print_text("Use /thread list to see available threads", PrintType.INFO)
        return

    previous_thread = app.state.active_thread
    if app.switch_thread(thread_id):
        new_thread = app.state.get_current_thread()
        name_display = f" (Name: {new_thread.name})" if new_thread.name else ""

        app.ui.print_text(f"Successfully switched to thread {thread_id}{name_display}", PrintType.SUCCESS)
        app.ui.print_text(
            f"Thread Stats:\n  Messages: {len(new_thread.messages)} | Context Files: {len(new_thread.context)}\n"
            f"Embedded Files: {len(new_thread.embedded_files)}",
            PrintType.INFO,
        )
        app.ui.chat_thread_update(new_thread.thread_id)
    else:
        app.ui.print_text(f"Failed to switch to thread {thread_id}", PrintType.ERROR)
        app.switch_thread(previous_thread)
        app.ui.chat_thread_update(previous_thread)


async def _handle_rename_thread(app: Any, args: argparse.Namespace) -> None:
    """Rename an existing message thread."""
    thread_id_to_rename = args.thread_id
    new_thread_name = None
    if hasattr(args, "name") and args.name:
        new_thread_name = " ".join(args.name).strip()
    else:
        app.ui.print_text("Error: No new name provided.", PrintType.ERROR)
        return

    if not re.match(r"^[\w\- ]{3,40}$", new_thread_name):
        app.ui.print_text(
            f"Error: Invalid new name '{new_thread_name}'. Name must be 3-40 alphanumerics, underscores, hyphens, or "
            "spaces.",
            PrintType.ERROR,
        )
        return

    if thread_id_to_rename not in app.state.threads:
        if f"thread_{thread_id_to_rename}" not in app.state.threads:
            app.ui.print_text(f"Error: Thread with ID '{thread_id_to_rename}' not found.", PrintType.ERROR)
            return
        thread_id_to_rename = f"thread_{thread_id_to_rename}"

    thread_to_rename: MessageThread = app.state.threads[thread_id_to_rename]
    old_display_name = thread_to_rename.name if thread_to_rename.name else thread_to_rename.thread_id

    if new_thread_name != thread_id_to_rename and new_thread_name in app.state.threads:
        app.ui.print_text(
            f"Error: The new name '{new_thread_name}' conflicts with an existing thread ID.", PrintType.ERROR
        )
        return

    thread_to_rename.set_name(new_thread_name)

    app.ui.print_text(
        f"Thread '{old_display_name}' (ID: {thread_id_to_rename}) successfully renamed to '{new_thread_name}'.",
        PrintType.SUCCESS,
    )
    app.ui.chat_thread_update(thread_id_to_rename)


def _thread_needs_name(thread_id: str, thread: MessageThread, router_thread_id: str) -> bool:
    """Return True when a user conversation thread has messages but no display name."""
    if thread_id == router_thread_id or thread.metadata.get("type") == "router":
        return False
    return bool(thread.messages) and not bool(thread.name and thread.name.strip())


def _first_user_message(thread: MessageThread) -> Optional[Dict[str, str]]:
    """Return the first user message in a provider-safe shape."""
    for message in thread.messages:
        if message.get("role") == "user" and message.get("content"):
            content = str(message["content"])
            if USER_INPUT_PREFIX in content:
                content = content.split(USER_INPUT_PREFIX, 1)[1].strip()
            return {"role": "user", "content": content}
    return None


def _extract_thread_name(response: Optional[str]) -> Optional[str]:
    """Extract and sanitize a thread name from the standard thread naming response."""
    if not response:
        return None
    text = response.strip()
    match = THREAD_NAME_PATTERN.search(text)
    if not match:
        tag_match = re.search(r"<thread_name>\s*([^<]{1,80})\s*</thread_name>", text, re.IGNORECASE)
        if tag_match:
            return _sanitize_thread_name(tag_match.group(1)) or None

        line_match = re.search(
            r"(?:^|\n)\s*(?:[-*]\s*)?(?:`{1,3})?Thread\s+name\s*:\s*[\"'`]*([^\n\"'`<]{1,80})",
            text,
            re.IGNORECASE,
        )
        if line_match:
            return _sanitize_thread_name(line_match.group(1)) or None

        lines = [line.strip(" `\"'") for line in text.splitlines() if line.strip()]
        if len(lines) == 1 and len(lines[0]) <= 80:
            return _sanitize_thread_name(lines[0]) or None

        return None
    return _sanitize_thread_name(match.group(1)) or None


async def _handle_name_all_threads(app: Any, worker_id: str) -> None:
    """Generate names for all unnamed threads using the low_cost_search profile."""
    router_thread_id = app.state.router_thread_id
    unnamed_threads = [
        thread
        for thread_id, thread in app.state.threads.items()
        if _thread_needs_name(thread_id, thread, router_thread_id)
    ]

    if not unnamed_threads:
        app.ui.print_text("No unnamed threads with messages found.", PrintType.INFO)
        return

    model = app.profile_manager().get_model("low_cost_search")
    thread_name_prompt = PromptManager.load("conversation/thread_name")
    app.ui.print_text(
        f"Naming {len(unnamed_threads)} unnamed thread(s) using {model} (low_cost_search profile)...",
        PrintType.PROCESSING,
    )

    named_count = 0
    skipped_count = 0
    failed_count = 0

    for thread in unnamed_threads:
        first_user_message = _first_user_message(thread)
        if not first_user_message:
            skipped_count += 1
            app.ui.print_text(
                f"Skipping {thread.thread_id}: no user message found.",
                PrintType.INFO,
            )
            continue

        name_request = (
            "Name this existing thread using the first user request below. "
            "Return only the final thread name line.\n\n"
            f"First request:\n{first_user_message['content']}"
        )
        messages = [{"role": "system", "content": thread_name_prompt}, {"role": "user", "content": name_request}]
        try:
            response = await generate_llm_response(
                app,
                model,
                messages,
                worker_id,
                print_stream=False,
                max_output_tokens=200,
            )
            thread_name = _extract_thread_name(response)
            if not thread_name:
                failed_count += 1
                app.ui.print_text(
                    f"Could not extract a valid name for {thread.thread_id}.",
                    PrintType.WARNING,
                )
                continue

            thread.set_name(thread_name)
            named_count += 1
            app.ui.print_text(f"Named {thread.thread_id}: {thread_name}", PrintType.SUCCESS)
            app.ui.chat_thread_update(thread.thread_id)
        except Exception as e:
            failed_count += 1
            app.logger.error("Failed to name thread %s: %s", thread.thread_id, e)
            app.ui.print_text(f"Failed to name {thread.thread_id}: {e}", PrintType.ERROR)

    app.ui.print_text(
        f"Thread naming complete: {named_count} named, {skipped_count} skipped, {failed_count} failed.",
        PrintType.SUCCESS if failed_count == 0 else PrintType.WARNING,
    )


async def _handle_thread_info(app: Any) -> None:
    """Show information about the current thread"""
    thread_id = app.state.active_thread
    thread = app.state.get_current_thread()

    message_count = len(thread.messages)
    context_count = len(thread.context)
    files_count = len(thread.embedded_files)
    name_display = f" (Name: {thread.name})" if thread.name else ""

    user_messages = sum(1 for msg in thread.messages if msg.get("role") == "user")
    assistant_messages = sum(1 for msg in thread.messages if msg.get("role") == "assistant")
    system_messages = sum(1 for msg in thread.messages if msg.get("role") == "system")

    app.ui.print_text(f"Thread ID: {thread_id}{name_display}", PrintType.HEADER)
    app.ui.print_text(f"Total messages: {message_count}", PrintType.INFO)
    app.ui.print_text(f"  User messages: {user_messages}", PrintType.INFO)
    app.ui.print_text(f"  Assistant messages: {assistant_messages}", PrintType.INFO)
    app.ui.print_text(f"  System messages: {system_messages}", PrintType.INFO)
    app.ui.print_text(f"Context files: {context_count}", PrintType.INFO)
    app.ui.print_text(f"Files referenced: {files_count}", PrintType.INFO)

    if context_count > 0:
        app.ui.print_text("Context files:", PrintType.INFO)
        for ctx_file in thread.context:
            app.ui.print_text(f"  {ctx_file}", PrintType.INFO)

    if message_count > 0:
        show_conversation(app, max_messages=5)


async def _handle_view_conversation(app: Any, args: argparse.Namespace) -> None:
    """View the conversation in the current thread"""
    max_messages = args.count
    show_conversation(app, max_messages=max_messages)


async def _handle_delete_thread(app: Any, args: argparse.Namespace) -> None:
    """Delete an existing message thread."""
    thread_id = args.thread_id
    success = app.state.delete_thread(thread_id)
    if not success:
        # also try adding thread_ prefix
        success = app.state.delete_thread(f"thread_{thread_id}")
        if not success:
            app.ui.print_text(f"Error: Thread '{thread_id}' not found or could not be deleted.", PrintType.ERROR)
            return
        thread_id = f"thread_{thread_id}"
    app.ui.print_text(f"Deleted thread: {thread_id}", PrintType.SUCCESS)
    app.ui.chat_thread_update(app.state.active_thread)


async def _handle_websearch_toggle(app: Any, args: argparse.Namespace) -> None:
    """Enable or disable per-thread web search mode.

    When enabled, chat input will route the user's message through the research agent
    rather than the default chat model for the active thread.
    """
    thread = app.state.get_current_thread()
    if not thread:
        app.ui.print_text("No active thread.", PrintType.ERROR)
        return

    enable = args.state.lower() == "on"
    thread.metadata["web_search_enabled"] = enable
    try:
        thread.save()  # Persist toggle if possible
    except Exception:
        # Non-fatal if persistence fails; runtime state still updated
        pass

    state_str = "enabled" if enable else "disabled"
    app.ui.print_text(f"Web search {state_str} for thread {thread.thread_id}", PrintType.SUCCESS)
    app.ui.chat_thread_update(thread.thread_id)
