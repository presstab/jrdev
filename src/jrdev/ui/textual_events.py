from typing import Any, List, Optional, Tuple
from textual.message import Message
from textual.containers import Horizontal
from textual.widgets import Button, Input
from jrdev.ui.ui_wrapper import UiWrapper
from jrdev.ui.ui import PrintType
import asyncio
import logging

# Get the global logger instance
logger = logging.getLogger("jrdev")

class TextualEvents(UiWrapper):
    def __init__(self, app):  # Add app reference
        super().__init__()
        self.ui_name = "textual"
        self.app = app  # Store reference to Textual app
        self.word_stream = ""
        self.confirmation_future = None
        self.steps_future = None

    class PrintMessage(Message):
        def __init__(self, text, print_type: PrintType = PrintType.INFO):
            super().__init__()
            self.text = text
            self.print_type: PrintType = print_type

    class TaskUpdate(Message):
        """Send the UI update info about a worker thread's activities"""
        def __init__(self, worker_id, update):
            super().__init__()
            self.worker_id = worker_id
            self.update = update

    class ModelChanged(Message):
        """Send the UI the new model"""
        def __init__(self, model):
            super().__init__()
            self.text = model

    class ModelListUpdated(Message):
        """Notify UI that model list has changed"""
        pass

    class ChatThreadUpdate(Message):
        def __init__(self, thread_id: str):
            super().__init__()
            self.thread_id = thread_id

    class CodeContextUpdate(Message):
        def __init__(self):
            super().__init__()

    class ProjectContextUpdate(Message):
        def __init__(self, is_enabled):
            super().__init__()
            self.is_enabled = is_enabled

    class StreamChunk(Message):
        """Fired once per text-chunk from the LLM."""
        def __init__(self, thread_id: str, chunk: str):
            super().__init__()
            self.thread_id = thread_id
            self.chunk = chunk

    class ConfirmationRequest(Message):
        def __init__(self, prompt_text: str, future: asyncio.Future, diff_lines: Optional[List[str]] = None, error_msg: str = None):
            super().__init__()
            self.prompt_text = prompt_text
            self.future = future
            self.diff_lines = diff_lines or []
            self.error_msg = error_msg
            
    class ConfirmationResponse(Message):
        def __init__(self, response: str, message: Optional[str] = None):
            super().__init__()
            self.response = response
            self.message = message

    class StepsRequest(Message):
        def __init__(self, steps: Any, future: asyncio.Future):
            super().__init__()
            self.steps = steps
            self.future = future

    class TextEditRequest(Message):
        """Message to request the UI to show a text editor."""
        def __init__(self, content_to_edit: List[str], prompt_message: str, future: asyncio.Future):
            super().__init__()
            self.content_to_edit = content_to_edit
            self.prompt_message = prompt_message
            self.future = future

    class ExitRequest(Message):
        """Signal to the Textual UI app that it should exit"""
        pass

    class EnterApiKeys(Message):
        """Signal to the UI that Api Keys need to be entered"""
        pass

    class DeletionRequest(Message):
        """Request confirmation for file deletion"""
        def __init__(self, filepath: str, future: asyncio.Future):
            super().__init__()
            self.filepath = filepath
            self.future = future

    class ProvidersUpdate(Message):
        """List of providers has changed (edit/add/delete)"""
        pass

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        # Post custom message when print is called
        if self.capture_active:
            self.capture += message
        self.app.post_message(self.PrintMessage(message, print_type))

    def print_stream(self, message: str):
        self.word_stream += message
        while '\n' in self.word_stream:
            line, self.word_stream = self.word_stream.split('\n', 1)
            self.app.post_message(self.PrintMessage(line))
            if self.capture_active:
                self.capture += line

    def update_task_info(self, worker_id: str, update: dict = None) -> None:
        self.app.post_message(self.TaskUpdate(worker_id, update))

    async def prompt_for_confirmation(self, prompt_text: str = "Apply these changes?", diff_lines: Optional[List[str]] = None, error_msg: None = "") -> Tuple[str, Optional[str]]:
        """
        Prompt the user for confirmation with options using Textual widgets.
        
        Args:
            prompt_text: The text to display when prompting the user
            diff_lines: Optional list of diff lines to display in the dialog
            error_msg: Optional error message to display if something has failed on a previous attempt
        Returns:
            Tuple of (response, message):
                - response: 'yes', 'no', 'request_change', 'edit', or 'accept_all'
                - message: User's feedback message when requesting changes,
                          or edited content when editing, None otherwise
        """
        # Create a future to wait for the response
        self.confirmation_future = asyncio.Future()
        
        # Send a message to the UI to show the confirmation dialog
        self.app.post_message(self.ConfirmationRequest(prompt_text, self.confirmation_future, diff_lines, error_msg))
        
        # Wait for the confirmation response
        result = await self.confirmation_future
        return result

    async def prompt_steps(self, steps: Any) -> Any:
        self.steps_future = asyncio.Future()
        self.app.post_message(self.StepsRequest(steps, self.steps_future))
        result = await self.steps_future
        return result

    async def prompt_for_text_edit(self, content_to_edit: List[str], prompt_message: str = "Edit File Content") -> Optional[List[str]]:
        """
        Prompts the user to edit a list of text lines using a modal editor.

        Args:
            content_to_edit: A list of strings representing the lines of content to be edited.
            prompt_message: A message/title to display on the editor screen.

        Returns:
            A list of strings representing the edited lines if the user saves changes,
            or None if the user cancels or an error occurs.
        """
        edit_future = asyncio.Future()
        self.app.post_message(self.TextEditRequest(content_to_edit, prompt_message, edit_future))
        result = await edit_future
        return result

    async def signal_no_keys(self):
        """
        Signal to UI that no api keys were found on startup
        Returns:
        """
        self.app.post_message(self.EnterApiKeys())

    async def signal_exit(self):
        """
        Signal to the Textual UI app that it should exit
        """
        self.app.post_message(self.ExitRequest())

    def model_changed(self, model):
        """
        Signal to UI that the selected model has changed
        Args:
            model: llm model selected in state
        """
        self.app.post_message(self.ModelChanged(model))

    def model_list_updated(self) -> None:
        """
        Signal to UI that model list has changed
        """
        self.app.post_message(self.ModelListUpdated())

    def chat_thread_update(self, thread_id):
        """
        Signal to UI that a chat thread has been updated
        """
        self.app.post_message(self.ChatThreadUpdate(thread_id))

    def code_context_update(self):
        """
        Signal to UI that code context has been updated
        """
        self.app.post_message(self.CodeContextUpdate())

    def project_context_changed(self, is_enabled: bool) -> None:
        """Signal to UI that project context has been toggled on or off"""
        self.app.post_message(self.ProjectContextUpdate(is_enabled))

    def stream_chunk(self, thread_id: str, chunk: str) -> None:
        """Post a chunk event into Textual's event bus."""
        self.app.post_message(self.StreamChunk(thread_id, chunk))

    def providers_updated(self) -> None:
        """Providers has been changed (add/delete/edit)"""
        self.app.post_message(self.ProvidersUpdate())

    async def prompt_for_deletion(self, filepath: str) -> bool:
        """
        Prompt the user for confirmation before deleting a file.
        
        Args:
            filepath: The path to the file that will be deleted
            
        Returns:
            bool: True if the user confirms deletion, False otherwise
        """
        deletion_future = asyncio.Future()
        self.app.post_message(self.DeletionRequest(filepath, deletion_future))
        result = await deletion_future
        return result
