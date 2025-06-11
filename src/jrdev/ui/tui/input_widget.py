from textual.color import Color
from textual.message import Message
from textual.binding import Binding
from textual.widgets import TextArea
from textual import events
from dataclasses import dataclass
from typing import ClassVar
import json
import logging
import os
from jrdev.file_operations.file_utils import get_persistent_storage_path


class CommandTextArea(TextArea):
    """A command input widget based on TextArea for multi-line input."""

    DEFAULT_CSS = """
    CommandTextArea {
        background: $surface;
        color: $foreground;
        border: tall $border-blurred;
        width: 100%;
        height: 3;  /* Default to 3 lines of height */

        &:focus {
            border: tall $border;
        }

        & .text-area--cursor {
            background: $input-cursor-background;
            color: $input-cursor-foreground;
            text-style: $input-cursor-text-style;
        }
    }
    """

    BINDINGS: ClassVar[list] = [
        # Retain most TextArea bindings but override enter/up/down behavior
        *[binding for binding in TextArea.BINDINGS if "enter" not in binding.key and "up" not in binding.key and "down" not in binding.key],
        Binding("enter", "submit", "Submit", show=False),
        Binding("up", "history_previous", "History Previous", show=False),
        Binding("down", "history_next", "History Next", show=False),
    ]

    @dataclass
    class Submitted(Message):
        """Posted when the enter key is pressed within the CommandTextArea."""

        text_area: "CommandTextArea"
        """The CommandTextArea widget that is being submitted."""

        value: str
        """The value of the CommandTextArea being submitted."""

        @property
        def control(self) -> "CommandTextArea":
            """Alias for self.text_area."""
            return self.text_area

    def __init__(
            self,
            placeholder: str = "Enter Command",
            id: str = "cmd_input",
            height: int = 3,
            **kwargs
    ):
        """Initialize the CommandTextArea widget.

        Args:
            placeholder: Optional placeholder text shown when empty.
            id: The ID of the widget.
            height: The height of the widget in lines (default: 3).
            **kwargs: Additional arguments to pass to TextArea.
        """
        super().__init__(id=id, **kwargs)
        self.border_title = placeholder
        self.styles.border = ("round", Color.parse("#63f554"))
        self.styles.height = height
        self._placeholder = placeholder

        # Disable features we don't need
        self.show_line_numbers = False

        # Load command history from persistent storage
        logger = logging.getLogger("jrdev")
        storage_path = get_persistent_storage_path()
        history_file = f"{storage_path}command_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    self.submit_history = json.load(f)
                    self.history_index = len(self.submit_history)
            except Exception as e:
                logger.error(f"Error loading command history: {e}")
                self.submit_history = []
                self.history_index = 0
        else:
            self.submit_history = []
            self.history_index = 0

        self._draft = None

    def render_line(self, y: int) -> "Strip":
        """Render a line of the widget, adding placeholder text if empty."""
        # Get the normal strip from the TextArea
        strip = super().render_line(y)

        # Show placeholder only on first line when document is empty
        if y == 0 and not self.text and strip.cell_length == 0:
            console = self.app.console
            from rich.text import Text

            placeholder = Text(
                self._placeholder,
                style="dim",
                end=""
            )

            # Create a new strip with the placeholder text
            placeholder_segments = list(console.render(placeholder))
            if placeholder_segments:
                from textual.strip import Strip
                return Strip(placeholder_segments)

        return strip

    def action_submit(self) -> None:
        """Handle the submit action when Enter is pressed."""
        if not self.text:
            # don't submit anything if empty
            return
        self.post_message(self.Submitted(self, self.text))
        self.submit_history.append(self.text)
        self.history_index = len(self.submit_history)

        # Save updated history
        storage_path = get_persistent_storage_path()
        history_file = f"{storage_path}command_history.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(self.submit_history, f)
        except Exception as e:
            logger = logging.getLogger("jrdev")
            logger.error(f"Error saving command history: {e}")

        # Optionally clear the input after submission
        self.clear()

    def action_history_previous(self) -> None:
        """Handle moving to previous history entry."""
        if not self.submit_history:
            return
        if self.history_index == len(self.submit_history):
            # Save current text as draft when entering history
            self._draft = self.text
        self.history_index = max(0, self.history_index - 1)
        self.text = self.submit_history[self.history_index]

    def action_history_next(self) -> None:
        """Handle moving to next history entry."""
        if not self.submit_history:
            return
        if self.history_index < len(self.submit_history):
            self.history_index += 1
            if self.history_index == len(self.submit_history):
                self.text = self._draft
            else:
                self.text = self.submit_history[self.history_index]

    async def _on_key(self, event: events.Key) -> None:
        """Intercept the key events to handle enter key for submission."""
        if event.key == "enter":
            # When Enter is pressed, submit instead of inserting a newline
            event.stop()
            event.prevent_default()
            self.action_submit()
        else:
            # For all other keys, use the default TextArea behavior
            await super()._on_key(event)
