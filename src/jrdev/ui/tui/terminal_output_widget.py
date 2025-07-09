from textual import events, on
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button
from typing import Optional
import logging
import pyperclip

from jrdev.ui.tui.input_widget import CommandTextArea
from jrdev.ui.tui.terminal_text_area import TerminalTextArea

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
    }
    """

    def __init__(self, id: Optional[str] = None, output_widget_mode=False) -> None:
        super().__init__(id=id)
        # output_widget_mode provides the output widget, without the input widget
        self.output_widget_mode = output_widget_mode
        self.terminal_output = TerminalTextArea(_id="terminal_output")
        self.copy_button = Button(label="Copy Selection", id="copy_button")
        if not self.output_widget_mode:
            self.terminal_input = CommandTextArea(placeholder="Enter Command", id="cmd_input")
        self.layout_output = Vertical(id="vlayout_output")

    def compose(self) -> ComposeResult:
        with self.layout_output:
            yield self.terminal_output
            yield self.copy_button
        if not self.output_widget_mode:
            yield self.terminal_input

    async def on_mount(self) -> None:
        self.can_focus = False
        self.terminal_output.can_focus = True
        self.copy_button.can_focus = True
        self.terminal_output.soft_wrap = True
        self.terminal_output.read_only = True
        self.terminal_output.show_line_numbers = False

        if self.output_widget_mode:
            self.styles.height = "1fr"
        else:
            self.terminal_input.focus()
            self.terminal_input.border_title = "Command Input"
            self.terminal_input.styles.border = ("round", Color.parse("#5e5e5e"))
            self.terminal_input.styles.border_title_color = "#fabd2f"
            self.terminal_input.styles.height = 6
            self.layout_output.border_title = "JrDev Terminal"
            self.layout_output.styles.border = ("round", Color.parse("#5e5e5e"))
            self.layout_output.styles.border_title_color = "#fabd2f"

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

    def clear_input(self):
        self.terminal_input.value = ""