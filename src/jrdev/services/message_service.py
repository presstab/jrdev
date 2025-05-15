from typing import AsyncIterator, TYPE_CHECKING
from jrdev.message_builder import MessageBuilder
from jrdev.llm_requests import stream_request
from jrdev.messages.thread import MessageThread

if TYPE_CHECKING:
    from jrdev.core.application import Application # To avoid circular imports

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
        # stream_request returns an async generator directly as per refactoring note (b)
        llm_response_stream = stream_request(
            self.app,
            self.app.state.model,
            messages_for_llm,
            task_id
        )

        async for chunk in llm_response_stream:
            response_accumulator += chunk
            msg_thread.add_response_partial(chunk) # Update thread with partial assistant response
            yield chunk

        # Finalize the full response in the message thread
        msg_thread.finalize_response(response_accumulator)
