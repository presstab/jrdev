from typing import Any, Optional
from textual.message import Message
from jrdev.ui.ui_wrapper import UiWrapper
from jrdev.ui.ui import PrintType

class TextualEvents(UiWrapper):
    class PrintMessage(Message):
        def __init__(self, text):
            super().__init__()
            self.text = text

    def __init__(self, app):  # Add app reference
        super().__init__()
        self.ui_name = "textual"
        self.app = app  # Store reference to Textual app
        self.word_stream = ""

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        # Post custom message when print is called
        self.app.post_message(self.PrintMessage(message))

    def print_stream(self, message:str):
        self.word_stream += message
        while '\n' in self.word_stream:
            line, self.word_stream = self.word_stream.split('\n', 1)
            self.app.post_message(self.PrintMessage(line))
