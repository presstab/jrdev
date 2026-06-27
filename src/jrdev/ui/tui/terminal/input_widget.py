from textual.color import Color
from textual.message import Message
from textual.binding import Binding
from textual.widgets import TextArea
from textual import events
from dataclasses import dataclass
from typing import ClassVar
import inspect
import json
import logging
import os
from jrdev.file_operations.file_utils import get_persistent_storage_path
import logging
logger = logging.getLogger("jrdev")


class CommandTextArea(TextArea):
    """A command input widget based on TextArea for multi-line input."""
    MAX_HISTORY = 20
    MIN_RESIZE_HEIGHT = 3
    RESIZE_HANDLE_DOT = "•"
    RESIZE_HANDLE_HIT_PADDING = 2

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
        Binding("shift+pagedown", "insert_newline", "Insert newline", show=False),
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

    def __setattr__(self, name, value):
        """Keep the resize handle visible when the border title is changed externally."""
        if name == "border_title" and isinstance(value, str) and value:
            value = self._format_border_title_with_resize_handle(value)
        super().__setattr__(name, value)

    @classmethod
    def _strip_resize_handle_from_title(cls, title: str) -> str:
        """Return the border title without the resize handle marker."""
        title = title.rstrip()
        handle_suffix = f" {cls.RESIZE_HANDLE_DOT}"
        if title.endswith(handle_suffix):
            return title[:-len(handle_suffix)].rstrip()
        if title.endswith(cls.RESIZE_HANDLE_DOT):
            return title[:-len(cls.RESIZE_HANDLE_DOT)].rstrip()
        return title

    @classmethod
    def _format_border_title_with_resize_handle(cls, title: str) -> str:
        """Append the resize handle marker to a border title, avoiding duplicates."""
        title_without_handle = cls._strip_resize_handle_from_title(title)
        return f"{title_without_handle} {cls.RESIZE_HANDLE_DOT}"

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
        self._resize_dragging = False
        self._resize_start_screen_y = 0
        self._resize_start_height = height

        # Disable features we don't need
        self.show_line_numbers = False

        # Load command history from persistent storage
        logger = logging.getLogger("jrdev")
        storage_path = get_persistent_storage_path()
        history_file = f"{storage_path}command_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    self.submit_history = json.load(f)[-self.MAX_HISTORY:]
                    self.history_index = len(self.submit_history)
            except Exception as e:
                logger.error(f"Error loading command history: {e}")
                self.submit_history = []
                self.history_index = 0
        else:
            self.submit_history = []
            self.history_index = 0

        self._draft = None

    def _get_plain_border_title(self) -> str:
        """Return the visible border title text without the resize handle marker."""
        border_title = getattr(self, "border_title", "") or ""
        return self._strip_resize_handle_from_title(str(border_title))

    def _get_event_position(self, event: events.MouseEvent) -> tuple[int, int]:
        """Return the mouse position relative to this widget when possible."""
        x = int(getattr(event, "x", 0))
        y = int(getattr(event, "y", 0))
        width = int(getattr(self.size, "width", 0) or 0)
        height = int(getattr(self.size, "height", 0) or 0)

        if 0 <= x < max(width, 1) and 0 <= y < max(height, 1):
            return x, y

        screen_x = int(getattr(event, "screen_x", x))
        screen_y = int(getattr(event, "screen_y", y))
        region = getattr(self, "region", None)
        if region is not None:
            return screen_x - int(region.x), screen_y - int(region.y)

        return x, y

    def _get_event_screen_y(self, event: events.MouseEvent) -> int:
        """Return a stable vertical coordinate for drag calculations."""
        return int(getattr(event, "screen_y", getattr(event, "y", 0)))

    def _is_resize_handle_event(self, event: events.MouseEvent) -> bool:
        """Check whether a mouse event occurred over the border title resize dot."""
        x, y = self._get_event_position(event)
        if y != 0:
            return False

        plain_title = self._get_plain_border_title()
        if not plain_title:
            return False

        # Textual renders left-aligned border titles just inside the left border.
        # The small hit window allows for border glyph spacing/theme differences.
        expected_dot_x = len(plain_title) + 3
        return abs(x - expected_dot_x) <= self.RESIZE_HANDLE_HIT_PADDING

    def _current_widget_height(self) -> int:
        """Return the current widget height in rows, falling back to the minimum."""
        current_height = int(getattr(self.size, "height", 0) or 0)
        return max(current_height, self.MIN_RESIZE_HEIGHT)

    def _capture_resize_mouse(self) -> None:
        """Capture mouse events while resizing, supporting multiple Textual versions."""
        capture_mouse = getattr(self, "capture_mouse", None)
        if callable(capture_mouse):
            capture_mouse()
            return

        app_capture_mouse = getattr(getattr(self, "app", None), "capture_mouse", None)
        if callable(app_capture_mouse):
            app_capture_mouse(self)

    def _release_resize_mouse(self) -> None:
        """Release mouse capture after resizing, supporting multiple Textual versions."""
        release_mouse = getattr(self, "release_mouse", None)
        if callable(release_mouse):
            release_mouse()
            return

        app_release_mouse = getattr(getattr(self, "app", None), "release_mouse", None)
        if callable(app_release_mouse):
            app_release_mouse()

    def _begin_resize_drag(self, event: events.MouseEvent) -> None:
        """Start resizing the command input height."""
        self._resize_dragging = True
        self._resize_start_screen_y = self._get_event_screen_y(event)
        self._resize_start_height = self._current_widget_height()
        self.focus()
        self._capture_resize_mouse()
        event.stop()
        event.prevent_default()

    def _update_resize_drag(self, event: events.MouseEvent) -> None:
        """Update the command input height while the resize handle is dragged."""
        # Negate delta_y so dragging UP (decreasing screen_y) increases height
        delta_y = self._resize_start_screen_y - self._get_event_screen_y(event)
        new_height = max(self.MIN_RESIZE_HEIGHT, self._resize_start_height + delta_y)
        if new_height != self._current_widget_height():
            self.styles.height = new_height
            self.refresh(layout=True)
        event.stop()
        event.prevent_default()

    def _end_resize_drag(self, event: events.MouseEvent) -> None:
        """Finish resizing the command input height."""
        self._resize_dragging = False
        self._release_resize_mouse()
        event.stop()
        event.prevent_default()

    async def _call_super_mouse_handler(self, handler_name: str, event: events.MouseEvent) -> None:
        """Call TextArea's mouse handler for normal editing interactions."""
        handler = getattr(super(), handler_name, None)
        if handler is None:
            return
        result = handler(event)
        if inspect.isawaitable(result):
            await result

    async def _on_mouse_down(self, event: events.MouseDown) -> None:
        """Start a resize drag when the border-title dot is pressed."""
        if self._is_resize_handle_event(event):
            self._begin_resize_drag(event)
            return
        await self._call_super_mouse_handler("_on_mouse_down", event)

    async def _on_mouse_move(self, event: events.MouseMove) -> None:
        """Resize vertically while dragging the border-title dot."""
        if self._resize_dragging:
            self._update_resize_drag(event)
            return
        await self._call_super_mouse_handler("_on_mouse_move", event)

    async def _on_mouse_up(self, event: events.MouseUp) -> None:
        """End a resize drag when the mouse button is released."""
        if self._resize_dragging:
            self._end_resize_drag(event)
            return
        await self._call_super_mouse_handler("_on_mouse_up", event)

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
        self.submit_history = self.submit_history[-self.MAX_HISTORY:]
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

    def action_insert_newline(self):
        self.insert("\n")

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