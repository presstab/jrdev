import pyperclip
import logging

from textual import on
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Vertical
from textual.widgets import Button
from jrdev.ui.tui.terminal_text_area import TerminalTextArea

logger = logging.getLogger("jrdev")

class MessageBubble(Vertical):
    """A widget to display a single chat message with a copy button."""

    DEFAULT_CSS = """
    MessageBubble {
        padding: 0;
        margin: 0 0; /* Vertical margin, 0 horizontal */
        width: 100%; 
        height: auto; 
    }
    MessageBubble > TerminalTextArea {
        height: auto; 
        border: none; 
        margin-bottom: 0; /* Space between text area and button */
    }
    MessageBubble > Button {
        dock: bottom;
        height: 1;
        width: auto;
        min-width: 8; /* "Copy" + padding */
    }
    """

    def __init__(self, message_content: str, role: str, id: str | None = None) -> None:
        super().__init__(id=id)
        self.message_content = message_content
        self.role = role
        self.is_thinking = message_content == "Thinking..."

        border_color_map = {
            "user": "green",
            "assistant": "cyan",
        }
        color = border_color_map.get(self.role, "grey")  # Default to grey if role is unknown
        
        self.styles.border = ("round", color)
        # Example: self.border_title = self.role.capitalize() # If you want a title

    def compose(self) -> ComposeResult:
        """Compose the message bubble with a text area and a copy button."""
        self.text_area = TerminalTextArea(_id=f"{self.id}-text_area")
        yield self.text_area
        yield Button("Copy Selection")

    def on_mount(self) -> None:
        """Called when the widget is mounted in the DOM."""
        self.text_area.read_only = True
        self.text_area.soft_wrap = True
        self.text_area.text = self.message_content
        self.text_area.cursor_blink = False # Already set in TerminalTextArea but good to be explicit
        self.text_area.show_line_numbers = False
        self.text_area.can_focus = False

        if self.role == "user":
            self.styles.border = ("round", Color.parse("#63f554"))
            self.border_title = "Me"
        else:
            self.styles.border = ("round", Color.parse("#27dfd0"))
            self.border_title = "Assistant"

    @on(Button.Pressed)
    async def handle_copy_button(self, event: Button.Pressed) -> None:
        """Handles the copy button press, copying selected or all text."""
        text_to_copy = self.text_area.selected_text or self.text_area.text
        
        if text_to_copy:
            try:
                pyperclip.copy(text_to_copy)
                self.notify("Copied to clipboard!", timeout=2)
            except pyperclip.PyperclipException as e:
                logger.error(f"Pyperclip error copying to clipboard: {e}")
                self.notify(f"Error copying: {e}", severity="error", timeout=3)
            except Exception as e:
                logger.error(f"Unexpected error copying to clipboard: {e}")
                self.notify("Copy failed (unexpected error)", severity="error", timeout=3)
        else:
            self.notify("Nothing to copy.", timeout=2)

    def append_chunk(self, chunk: str) -> None:
        """Appends a chunk of text to the message bubble's text area for streaming."""
        # if this was previously in thinking state, clear the thinking message
        if self.is_thinking:
            self.text_area.clear()
            self.is_thinking = False

            # often the first chunks after thinking will be new lines
            while chunk.startswith("\n"):
                chunk = chunk.removeprefix("\n")

        # add the new text
        self.text_area.append_text(chunk)
