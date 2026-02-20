import pyperclip
import logging
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import Vertical, Horizontal
from textual.widgets import Button
from textual.message import Message
from jrdev.ui.tui.terminal.terminal_text_area import TerminalTextArea

logger = logging.getLogger("jrdev")

class MessageBubble(Vertical):
    """A widget to display a single chat message with copy, edit, and delete buttons."""

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
    .bubble_actions {
        dock: bottom;
        height: 1;
        width: 100%;
        layout: horizontal;
    }
    .bubble_btn {
        height: 1;
        width: auto;
        min-width: 6;
        margin-right: 1;
        border: none;
    }
    .bubble_btn:hover {
        text-style: reverse;
    }
    """

    class MessageEdited(Message):
        def __init__(self, thread_id: str, index: int, content: str) -> None:
            self.thread_id = thread_id
            self.index = index
            self.content = content
            super().__init__()

    class MessageDeleted(Message):
        def __init__(self, thread_id: str, index: int) -> None:
            self.thread_id = thread_id
            self.index = index
            super().__init__()

    def __init__(self, message_content: str, role: str, thread_id: str, message_index: int, id: str | None = None) -> None:
        super().__init__(id=id)
        self.message_content = message_content
        self.role = role
        self.thread_id = thread_id
        self.message_index = message_index
        self.is_thinking = message_content == "Thinking..."
        self.is_editing = False
        self.is_deleting = False

        border_color_map = {
            "user": "green",
            "assistant": "cyan",
        }
        color = border_color_map.get(self.role, "grey")  # Default to grey if role is unknown
        
        self.styles.border = ("round", color)

    def compose(self) -> ComposeResult:
        """Compose the message bubble with a text area and action buttons."""
        self.text_area = TerminalTextArea(_id=f"{self.id}-text_area")
        yield self.text_area

        with Horizontal(classes="bubble_actions"):
            yield Button("Copy", id="copy_btn", classes="bubble_btn")
            yield Button("Edit", id="edit_btn", classes="bubble_btn")
            yield Button("Delete", id="delete_btn", classes="bubble_btn")
            # Create hidden buttons for edit/delete confirmation/actions
            yield Button("Save", id="save_btn", classes="bubble_btn")
            yield Button("Cancel", id="cancel_btn", classes="bubble_btn")
            yield Button("Confirm Delete", id="confirm_delete_btn", classes="bubble_btn")

    def on_mount(self) -> None:
        """Called when the widget is mounted in the DOM."""
        self.text_area.read_only = True
        self.text_area.soft_wrap = True
        self.text_area.text = self.message_content
        self.text_area.cursor_blink = False
        self.text_area.show_line_numbers = False
        self.text_area.can_focus = False

        # Hide edit controls initially
        self.query_one("#save_btn").visible = False
        self.query_one("#cancel_btn").visible = False
        self.query_one("#confirm_delete_btn").visible = False

        if self.role == "user":
            self.styles.border = ("round", Color.parse("#63f554"))
            self.border_title = "Me"
        else:
            self.styles.border = ("round", Color.parse("#27dfd0"))
            self.border_title = "Assistant"

    @on(Button.Pressed, "#copy_btn")
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

    @on(Button.Pressed, "#edit_btn")
    async def handle_edit_start(self, event: Button.Pressed) -> None:
        self.is_editing = True
        self.text_area.read_only = False
        self.text_area.can_focus = True
        self.text_area.focus()

        self.query_one("#copy_btn").visible = False
        self.query_one("#edit_btn").visible = False
        self.query_one("#delete_btn").visible = False
        self.query_one("#save_btn").visible = True
        self.query_one("#cancel_btn").visible = True
        self.query_one("#confirm_delete_btn").visible = False

    @on(Button.Pressed, "#cancel_btn")
    async def handle_edit_cancel(self, event: Button.Pressed) -> None:
        self.is_editing = False
        self.is_deleting = False
        self.text_area.read_only = True
        self.text_area.can_focus = False
        # Revert text changes
        self.text_area.text = self.message_content

        self.query_one("#copy_btn").visible = True
        self.query_one("#edit_btn").visible = True
        self.query_one("#delete_btn").visible = True
        self.query_one("#save_btn").visible = False
        self.query_one("#cancel_btn").visible = False
        self.query_one("#confirm_delete_btn").visible = False

    @on(Button.Pressed, "#save_btn")
    async def handle_edit_save(self, event: Button.Pressed) -> None:
        new_content = self.text_area.text
        self.post_message(self.MessageEdited(self.thread_id, self.message_index, new_content))

        self.message_content = new_content

        # Reset UI
        self.is_editing = False
        self.text_area.read_only = True
        self.text_area.can_focus = False

        self.query_one("#copy_btn").visible = True
        self.query_one("#edit_btn").visible = True
        self.query_one("#delete_btn").visible = True
        self.query_one("#save_btn").visible = False
        self.query_one("#cancel_btn").visible = False
        self.query_one("#confirm_delete_btn").visible = False


    @on(Button.Pressed, "#delete_btn")
    async def handle_delete_start(self, event: Button.Pressed) -> None:
        self.is_deleting = True
        self.query_one("#copy_btn").visible = False
        self.query_one("#edit_btn").visible = False
        self.query_one("#delete_btn").visible = False
        self.query_one("#save_btn").visible = False
        self.query_one("#cancel_btn").visible = True
        self.query_one("#confirm_delete_btn").visible = True

    @on(Button.Pressed, "#confirm_delete_btn")
    async def handle_delete_confirm(self, event: Button.Pressed) -> None:
        self.post_message(self.MessageDeleted(self.thread_id, self.message_index))

    def append_chunk(self, chunk: str) -> None:
        """Appends a chunk of text to the message bubble's text area for streaming."""
        if self.is_thinking:
            self.text_area.clear()
            self.is_thinking = False

            while chunk.startswith("\n"):
                chunk = chunk.removeprefix("\n")

        self.text_area.append_text(chunk)
