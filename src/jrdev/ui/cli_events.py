from jrdev.ui.ui import terminal_print, PrintType
from jrdev.ui.ui_wrapper import UiWrapper
from typing import Any, Optional

class CliEvents(UiWrapper):
    def __init__(self):  # Add app reference
        super().__init__()
        self.ui_name = "cli"

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        # Post custom message when print is called
        terminal_print(message, print_type, end, prefix, flush)

    def print_stream(self, message:str):
        """print a stream of text"""
        terminal_print(message, PrintType.LLM, end="", flush=True)