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
    class PrintMessage(Message):
        def __init__(self, text):
            super().__init__()
            self.text = text
            
    class ConfirmationRequest(Message):
        def __init__(self, prompt_text: str, future: asyncio.Future, diff_lines: Optional[List[str]] = None):
            super().__init__()
            self.prompt_text = prompt_text
            self.future = future
            self.diff_lines = diff_lines or []
            
    class ConfirmationResponse(Message):
        def __init__(self, response: str, message: Optional[str] = None):
            super().__init__()
            self.response = response
            self.message = message
            
    class ExitRequest(Message):
        """Signal to the Textual UI app that it should exit"""
        pass

    class EnterApiKeys(Message):
        """Signal to the UI that Api Keys need to be entered"""
        pass

    def __init__(self, app):  # Add app reference
        super().__init__()
        self.ui_name = "textual"
        self.app = app  # Store reference to Textual app
        self.word_stream = ""
        self.confirmation_future = None

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        # Post custom message when print is called
        self.app.post_message(self.PrintMessage(message))

    def print_stream(self, message: str):
        self.word_stream += message
        while '\n' in self.word_stream:
            line, self.word_stream = self.word_stream.split('\n', 1)
            self.app.post_message(self.PrintMessage(line))
            
    async def prompt_for_confirmation(self, prompt_text: str = "Apply these changes?", diff_lines: Optional[List[str]] = None) -> Tuple[str, Optional[str]]:
        """
        Prompt the user for confirmation with options using Textual widgets.
        
        Args:
            prompt_text: The text to display when prompting the user
            diff_lines: Optional list of diff lines to display in the dialog
            
        Returns:
            Tuple of (response, message):
                - response: 'yes', 'no', 'request_change', or 'edit'
                - message: User's feedback message when requesting changes,
                          or edited content when editing, None otherwise
        """
        # Create a future to wait for the response
        self.confirmation_future = asyncio.Future()
        
        # Send a message to the UI to show the confirmation dialog
        self.app.post_message(self.ConfirmationRequest(prompt_text, self.confirmation_future, diff_lines))
        
        # Wait for the confirmation response
        result = await self.confirmation_future
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
