from typing import Any, Optional
from jrdev.ui.ui import PrintType

class UiWrapper:
    def __init__(self):
        self.ui_name = ""

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement print_text()")

    def print_stream(self, message:str):
        """print a stream of text"""
        raise NotImplementedError("Subclasses must implement print_text()")