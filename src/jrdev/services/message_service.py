from typing import AsyncIterator, TYPE_CHECKING
from jrdev.messages.message_builder import MessageBuilder
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.llm_requests import stream_request
from jrdev.messages.thread import MessageThread
import re
import logging

logger = logging.getLogger("jrdev")

if TYPE_CHECKING:
    from jrdev.core.application import Application # To avoid circular imports

THREAD_NAME_PATTERN = re.compile(r"\n?\s*Thread name:\s*([A-Za-z0-9 _-]{1,40})\s*$", re.IGNORECASE)

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


def _sanitize_thread_name(name: str) -> str:
    """Return a safe, short thread display name from model output."""
    safe_name = re.sub(r"[^A-Za-z0-9 _-]", "", name)
    safe_name = re.sub(r"\s+", " ", safe_name).strip(" _-")
    return safe_name[:15].strip(" _-")


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

        request_thread_name = not msg_thread.messages and not msg_thread.name

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

        persisted_messages = builder.build()
        messages_for_llm = persisted_messages
        if request_thread_name:
            thread_name_prompt = PromptManager.load("conversation/thread_name")
            messages_for_llm = [{"role": "system", "content": thread_name_prompt}, *messages_for_llm]

        # Update message thread state with the new user message and context used
        # This ensures the user's message is part of the history before the assistant responds.
        msg_thread.add_embedded_files(builder.get_files()) # Files used are now "embedded"
        msg_thread.messages = persisted_messages # Update thread history to include this user's message

        # Stream response from LLM
        response_accumulator = ""
        try:
            # stream_request returns an async generator directly as per refactoring note (b)
            response_model = self.app.state.model
            llm_response_stream = stream_request(
                self.app,
                response_model,
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
                        msg_thread.add_response_partial(chunk, model=response_model)  # Update thread with partial assistant response
                        yield chunk
                elif in_think:
                    if chunk == "</think>":
                        in_think = False
                else:
                    response_accumulator += chunk
                    msg_thread.add_response_partial(chunk, model=response_model) # Update thread with partial assistant response
                    yield chunk

            # Finalize the full response in the message thread
            final_response = response_accumulator.strip()
            if request_thread_name:
                match = THREAD_NAME_PATTERN.search(final_response)
                if match:
                    thread_name = _sanitize_thread_name(match.group(1))
                    if thread_name:
                        msg_thread.set_name(thread_name)
                    final_response = THREAD_NAME_PATTERN.sub("", final_response).rstrip()
            msg_thread.finalize_response(final_response, model=response_model)
        except Exception as e:
            logger.error("Message Service: %s", e)
            if task_id:
                self.app.ui.update_task_info(worker_id=task_id, update={"error": e})
