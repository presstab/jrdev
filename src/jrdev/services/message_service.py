from typing import AsyncIterator, TYPE_CHECKING
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import stream_request
from jrdev.messages.thread import MessageThread
import re
import logging

logger = logging.getLogger("jrdev")

if TYPE_CHECKING:
    from jrdev.core.application import Application # To avoid circular imports

def filter_think_tags(text):
    """Remove content within <think></think> tags."""
    # Use regex to remove all <think>...</think> sections
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)


def is_inside_think_tag(text):
    """Determine if the current position is inside a <think> tag."""
    # Count the number of opening and closing tags
    think_open = text.count("<think>")
    think_close = text.count("</think>")

    # If there are more opening tags than closing tags, we're inside a tag
    return think_open > think_close

class MessageService:
    def __init__(self, application: 'Application'):
        self.app = application
        self.logger = application.logger

    async def stream_message(self, msg_thread: MessageThread, content: str, task_id: str = None) -> AsyncIterator[str]:
        """
        Build the user+context messages, send the chat to the LLM as a stream,
        and yield each chunk of text as it arrives.
        """
        builder = MessageBuilder(self.app)
        # Configure builder with history and context
        builder.set_embedded_files(msg_thread.embedded_files)

        if msg_thread.messages:
            builder.add_historical_messages(msg_thread.messages)
        elif self.app.state.use_project_context: # Add project files if no history and project context is on
            builder.add_project_files()

        if msg_thread.context: # Add any files explicitly added to this thread's context
            builder.add_context(list(msg_thread.context))

        # Add the current user message
        builder.start_user_section()
        builder.append_to_user_section(content)
        builder.finalize_user_section()

        messages_for_llm = builder.build()

        # Update message thread state with the new user message and context used
        # This ensures the user's message is part of the history before the assistant responds.
        msg_thread.add_embedded_files(builder.get_files()) # Files used are now "embedded"
        msg_thread.messages = messages_for_llm # Update thread history to include this user's message

        # Stream response from LLM
        response_accumulator = ""
        try:
            # stream_request returns an async generator directly as per refactoring note (b)
            llm_response_stream = stream_request(
                self.app,
                self.app.state.model,
                messages_for_llm,
                task_id
            )

            # completely filter out thinking
            is_first_chunk = True
            in_think = False
            async for chunk in llm_response_stream:
                if is_first_chunk:
                    is_first_chunk = False
                    if chunk == "<think>":
                        in_think = True
                        yield "Thinking..."
                    else:
                        response_accumulator += chunk
                        msg_thread.add_response_partial(chunk)  # Update thread with partial assistant response
                        yield chunk
                elif in_think:
                    if chunk == "</think>":
                        in_think = False
                else:
                    response_accumulator += chunk
                    msg_thread.add_response_partial(chunk) # Update thread with partial assistant response
                    yield chunk

            # Finalize the full response in the message thread
            msg_thread.finalize_response(response_accumulator.strip())
        except Exception as e:
            logger.error("Message Service: %s", e)
            if task_id:
                self.app.ui.update_task_info(worker_id=task_id, update={"error": e})
