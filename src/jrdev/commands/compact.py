#!/usr/bin/env python3

"""
Compact command for JrDev.
Compacts conversation history to reduce token usage.
"""

import json
import logging
from typing import Any, List, Protocol

from jrdev.file_operations.file_utils import cutoff_string
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


# Define a Protocol for Application to avoid circular imports
class ApplicationProtocol(Protocol):
    model: str
    logger: logging.Logger


def _show_compact_help(app: Any) -> None:
    """
    Display help information for the /compact command.
    """
    app.ui.print_text("Compact Command Usage:", PrintType.HEADER)
    app.ui.print_text(
        "/compact --help - Show this help message",
        PrintType.INFO,
    )
    app.ui.print_text(
        "/compact - Compact the current conversation history to reduce token usage",
        PrintType.INFO,
    )
    app.ui.print_text("", PrintType.INFO)
    app.ui.print_text("Purpose:", PrintType.HEADER)
    app.ui.print_text(
        "The /compact command summarizes the entire conversation in the current chat thread.",
        PrintType.INFO,
    )
    app.ui.print_text(
        "This reduces the number of tokens used in future requests, helping to avoid context length limits and lower "
        "costs.",
        PrintType.INFO,
    )
    app.ui.print_text("", PrintType.INFO)
    app.ui.print_text("How it works:", PrintType.HEADER)
    app.ui.print_text(
        "- The command sends the conversation history to the AI model, which returns a compacted summary.",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- The conversation is then replaced with just summary messages, which is all the AI model will see going "
        "forward.",
        PrintType.INFO,
    )
    app.ui.print_text("", PrintType.INFO)
    app.ui.print_text("When to use:", PrintType.HEADER)
    app.ui.print_text(
        "- Use /compact when your conversation is getting long or you see warnings about token limits.",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- Compacting helps keep the conversation manageable and efficient.",
        PrintType.INFO,
    )
    app.ui.print_text(
        "- Note: Any context that was manually added to the chat using /addcontext will be removed and will need to be "
        "added again manually, if desired.",
        PrintType.INFO,
    )


async def handle_compact(app: Any, args: List[str], worker_id: str) -> None:
    """
    Compacts the current conversation history into a concise two-message summary.

    This command sends the entire conversation to an AI model and replaces the
    history with a summary. It is useful for reducing token usage in long-running
    conversations, but it is a destructive action for the detailed history.

    Usage:
      /compact
      /compact --help - Shows detailed information about the command.
    """
    if "--help" in args:
        _show_compact_help(app)
        return

    app.ui.print_text(
        "Compacting conversation history...",
        PrintType.INFO,
    )

    # thread to be compacted
    chat_thread = app.get_current_thread()

    # Use MessageBuilder to construct messages
    builder = MessageBuilder(app)
    builder.messages = chat_thread.messages
    builder.start_user_section()
    builder.load_user_prompt("conversation/compact")
    messages = builder.build()

    # Send request
    try:
        app.ui.print_text(
            f"\n{app.state.model} is compacting conversation...\n",
            PrintType.PROCESSING,
        )

        response = await generate_llm_response(app, app.state.model, messages, worker_id, print_stream=True)

        if response is not None:
            # Parse the JSON response
            try:
                cut_response = cutoff_string(response, "```json", "```")
                compact_data = json.loads(str(cut_response))

                # Verify the required fields are present
                if "user" not in compact_data or "assistant" not in compact_data:
                    raise ValueError("Response is missing required 'user' or 'assistant' fields")

                # Create new messages in the required format
                new_messages = [
                    {"role": "user", "content": compact_data["user"]},
                    {"role": "assistant", "content": compact_data["assistant"]},
                ]

                # Replace the thread's messages with just these two
                chat_thread.set_compacted(new_messages)
                app.ui.print_text("Conversation successfully compacted to two messages.", PrintType.SUCCESS)

                # notify ui of thread change
                app.ui.chat_thread_update(chat_thread.thread_id)

            except json.JSONDecodeError:
                app.ui.print_text(
                    "Error: Response is not valid JSON. Unable to compact conversation.",
                    PrintType.ERROR,
                )
                app.logger.error("Compact command received non-JSON response")

            except ValueError as e:
                app.ui.print_text(
                    f"Error: {str(e)}",
                    PrintType.ERROR,
                )
                app.logger.error(f"Compact command error: {str(e)}")

    except Exception as e:
        app.logger.error(f"Failed to compact conversation: {str(e)}")
        app.ui.print_text(
            "An error occurred while compacting the conversation.",
            PrintType.ERROR,
        )
        app.ui.print_text(
            f"Error details: {str(e)}",
            PrintType.ERROR,
        )
