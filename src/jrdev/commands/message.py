import argparse
from typing import Any, List
from jrdev.ui.ui import PrintType

async def handle_message(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Manage individual messages.

    Usage:
      /message edit <thread_id> <index> <content...>
      /message delete <thread_id> <index>
    """
    if len(args) < 2:
        return

    subcommand = args[1]

    if subcommand == "edit":
        if len(args) < 5:
            app.ui.print_text("Usage: /message edit <thread_id> <index> <content...>", PrintType.ERROR)
            return

        thread_id = args[2]
        try:
            index = int(args[3])
        except ValueError:
            app.ui.print_text("Error: index must be an integer", PrintType.ERROR)
            return

        content = " ".join(args[4:])

        thread = app.state.threads.get(thread_id)
        if not thread:
            # try prefix
            thread_id_pre = f"thread_{thread_id}"
            thread = app.state.threads.get(thread_id_pre)
            if thread:
                thread_id = thread_id_pre

        if not thread:
            app.ui.print_text(f"Error: Thread '{thread_id}' not found.", PrintType.ERROR)
            return

        if thread.edit_message(index, content):
            app.ui.print_text("Message updated.", PrintType.SUCCESS)
            app.ui.chat_thread_update(thread_id)
        else:
            app.ui.print_text("Error: Failed to update message (invalid index?)", PrintType.ERROR)

    elif subcommand == "delete":
        if len(args) < 4:
            app.ui.print_text("Usage: /message delete <thread_id> <index>", PrintType.ERROR)
            return

        thread_id = args[2]
        try:
            index = int(args[3])
        except ValueError:
            app.ui.print_text("Error: index must be an integer", PrintType.ERROR)
            return

        thread = app.state.threads.get(thread_id)
        if not thread:
            # try prefix
            thread_id_pre = f"thread_{thread_id}"
            thread = app.state.threads.get(thread_id_pre)
            if thread:
                thread_id = thread_id_pre

        if not thread:
            app.ui.print_text(f"Error: Thread '{thread_id}' not found.", PrintType.ERROR)
            return

        if thread.delete_message(index):
            app.ui.print_text("Message deleted.", PrintType.SUCCESS)
            app.ui.chat_thread_update(thread_id)
        else:
            app.ui.print_text("Error: Failed to delete message (invalid index?)", PrintType.ERROR)

    else:
        app.ui.print_text(f"Unknown message subcommand: {subcommand}", PrintType.ERROR)
