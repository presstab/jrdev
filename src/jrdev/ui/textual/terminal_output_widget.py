from textual import events, on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Button, TextArea
from textual.color import Color
from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional
import logging
import pyperclip
from textual.color import Color

logger = logging.getLogger("jrdev")

class TerminalOutputWidget(Widget):
    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.terminal_output = TextArea(id="terminal_output", language="plaintext")
        self.copy_button = Button(label="Copy Selection", id="copy_button")
        self.copy_button.on_click = self.copy_to_clipboard

    def compose(self) -> ComposeResult:
        yield self.terminal_output
        yield self.copy_button

    async def on_mount(self) -> None:
        self.can_focus = False
        self.terminal_output.can_focus = False
        self.copy_button.can_focus = False

        self.terminal_output.styles.border = "none"

        self.terminal_output.soft_wrap = True
        self.terminal_output.read_only = True
        self.terminal_output.show_line_numbers = False

    @on(Button.Pressed, "#copy_button")
    def handle_copy(self):
        self.copy_to_clipboard()

    def copy_to_clipboard(self) -> None:
        # Logic to copy the selected text of the TextArea to the clipboard
        if not self.terminal_output.value:
            return

        if self.terminal_output.selected_text:
            content = self.terminal_output.selected_text
        else:
            content = self.terminal_output.value
        # Use pyperclip to copy to clipboard
        pyperclip.copy(content)
        # Provide visual feedback
        self.notify("Text copied to clipboard", timeout=2)
