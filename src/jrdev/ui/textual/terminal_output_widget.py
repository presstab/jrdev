from textual import events, on
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button
from typing import Optional
import logging
import pyperclip

from jrdev.ui.textual.terminal_text_area import TerminalTextArea

logger = logging.getLogger("jrdev")

class TerminalOutputWidget(Widget):
    # Default compose stacks vertically, which is fine.
    # Using Vertical explicitly offers more control if needed later.
    DEFAULT_CSS = """
    TerminalOutputWidget {
        /* Layout for children: Text Area grows, Button stays at bottom */
        layout: vertical;
    }
    #terminal_output {
        height: 1fr; /* Ensure text area takes available vertical space */
        width: 100%;
        border: none; /* Confirm no border */
    }
    #copy_button {
        height: 1; /* Fixed height */
        width: auto;
        align-horizontal: left;
        dock: bottom; /* Keep button at the bottom */
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.terminal_output = TerminalTextArea(id="terminal_output", language="plaintext")
        self.copy_button = Button(label="Copy Selection", id="copy_button")

    def compose(self) -> ComposeResult:
        yield self.terminal_output
        yield self.copy_button

    async def on_mount(self) -> None:
        self.can_focus = False
        self.terminal_output.can_focus = True
        self.copy_button.can_focus = True
        self.terminal_output.soft_wrap = True
        self.terminal_output.read_only = True
        self.terminal_output.show_line_numbers = False

    @on(Button.Pressed, "#copy_button")
    def handle_copy(self):
        self.copy_to_clipboard()

    def copy_to_clipboard(self) -> None:
        # Logic to copy the selected text of the TextArea to the clipboard
        if not self.terminal_output.text:
            return

        if self.terminal_output.selected_text:
            content = self.terminal_output.selected_text
        else:
            content = self.terminal_output.text
        # Use pyperclip to copy to clipboard
        pyperclip.copy(content)
        # Provide visual feedback
        self.notify("Text copied to clipboard", timeout=2)
        
    def append_text(self, text: str) -> None:
        """Append text to the end of the terminal output regardless of cursor position.
        
        This method preserves the current selection and scrolls to the bottom after appending,
        but only if the user is already at or near the bottom. If the user has scrolled away
        from the bottom, the scroll position is preserved.
        
        Args:
            text: The text to append to the terminal output.
        """
        self.terminal_output.append_text(text)