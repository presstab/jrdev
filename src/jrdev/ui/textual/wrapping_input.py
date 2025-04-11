from rich.text import Text
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import TextArea # Import TextArea
from textual.widgets._text_area import Selection # Import Selection
from textual import events # Import events for on_mount etc.
from typing import Any, Generator, List, Optional, Tuple, ClassVar, TYPE_CHECKING

# Import ScrollView to use super(ScrollView, self)
from textual.scroll_view import ScrollView


from rich.console import RenderableType
from textual.strip import Strip
from textual.widget import Widget # Import Widget for super() call target

class WrappingInput(TextArea):
    """
    An Input-like widget that wraps text and adjusts its height dynamically.

    Based on the TextArea widget.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        # ... (Bindings remain the same as before) ...
        Binding("up", "cursor_up", "Cursor up", show=False),
        Binding("down", "cursor_down", "Cursor down", show=False),
        Binding("left", "cursor_left", "Cursor left", show=False),
        Binding("right", "cursor_right", "Cursor right", show=False),
        Binding("ctrl+left", "cursor_word_left", "Cursor word left", show=False),
        Binding("ctrl+right", "cursor_word_right", "Cursor word right", show=False),
        Binding("home,ctrl+a", "cursor_line_start", "Cursor line start", show=False),
        Binding("end,ctrl+e", "cursor_line_end", "Cursor line end", show=False),
        Binding("pageup", "cursor_page_up", "Cursor page up", show=False),
        Binding("pagedown", "cursor_page_down", "Cursor page down", show=False),
        Binding(
            "ctrl+shift+left",
            "cursor_word_left(True)",
            "Cursor left word select",
            show=False,
        ),
        Binding(
            "ctrl+shift+right",
            "cursor_word_right(True)",
            "Cursor right word select",
            show=False,
        ),
        Binding(
            "shift+home",
            "cursor_line_start(True)",
            "Cursor line start select",
            show=False,
        ),
        Binding(
            "shift+end", "cursor_line_end(True)", "Cursor line end select", show=False
        ),
        Binding("shift+up", "cursor_up(True)", "Cursor up select", show=False),
        Binding("shift+down", "cursor_down(True)", "Cursor down select", show=False),
        Binding("shift+left", "cursor_left(True)", "Cursor left select", show=False),
        Binding("shift+right", "cursor_right(True)", "Cursor right select", show=False),
        Binding("backspace", "delete_left", "Delete character left", show=False),
        Binding(
            "ctrl+w", "delete_word_left", "Delete left to start of word", show=False
        ),
        Binding("delete,ctrl+d", "delete_right", "Delete character right", show=False),
        Binding(
            "ctrl+f", "delete_word_right", "Delete right to start of word", show=False
        ),
        Binding("ctrl+x", "cut", "Cut", show=False),
        Binding("ctrl+c", "copy", "Copy", show=False),
        Binding("ctrl+v", "paste", "Paste", show=False),
        Binding(
            "ctrl+u", "delete_to_start_of_line", "Delete to line start", show=False
        ),
        Binding(
            "ctrl+k",
            "delete_to_end_of_line_or_delete_line",
            "Delete to line end",
            show=False,
        ),
        Binding("enter", "submit", "Submit", show=False),
    ]

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        # ... (Component classes remain the same) ...
        "text-area--cursor",
        "text-area--gutter",
        "text-area--cursor-gutter",
        "text-area--cursor-line",
        "text-area--selection",
        "text-area--matching-bracket",
        "wrapping-input--placeholder",
    }

    DEFAULT_CSS = """
    WrappingInput {
        /* ... (CSS remains the same) ... */
        background: $surface;
        color: $foreground;
        padding: 0 1;
        border: tall $border-blurred;
        height: 3;
        width: 1fr;
        scrollbar-size-vertical: 0;
        scrollbar-size-horizontal: 0;

        &:focus {
            border: tall $border;
            background-tint: $foreground 5%;
        }
        & .text-area--cursor {
            background: $input-cursor-background;
            color: $input-cursor-foreground;
            text-style: $input-cursor-text-style;
        }
        & .text-area--selection {
            background: $input-selection-background;
        }
        & .wrapping-input--placeholder {
            color: $text-disabled;
        }
        &.-invalid {
            border: tall $error 60%;
        }
        &.-invalid:focus {
            border: tall $error;
        }
        &:ansi {
            background: ansi_default;
            color: ansi_default;
            & .text-area--cursor {
                text-style: reverse;
            }
            & .text-area--selection {
                background: transparent;
                text-style: reverse;
            }
            & .wrapping-input--placeholder {
                text-style: dim;
                color: ansi_default;
            }
            &.-invalid {
                border: tall ansi_red;
            }
            &.-invalid:focus {
                border: tall ansi_red;
            }
        }
    }
    """

    placeholder: reactive[str] = reactive("", layout=True)
    """Text that is displayed when the input is empty."""

    # --- Custom Messages ---
    class Submitted(Message):
        # ... (Submitted message remains the same) ...
        def __init__(self, input: Any, value: str) -> None:
            self.input = input
            self.value = value
            super().__init__()

        @property
        def control(self) -> Any:
            return self.input

    # --- Initialization ---
    def __init__(
        self,
        # ... (Init parameters remain the same) ...
        value: str = "",
        placeholder: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        tooltip: RenderableType | None = None,
        language: str | None = None,
        theme: str = "css",
    ) -> None:
        # ... (Init logic remains the same) ...
        super().__init__(
            text=value,
            language=language,
            theme=theme,
            soft_wrap=True,
            show_line_numbers=False,
            tab_behavior="focus",
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            tooltip=tooltip,
        )
        self.placeholder = placeholder
        self._initial_value_set = False
        if value:
            self._initial_value_set = True

    # --- Internal Logic ---
    def _update_height(self) -> None:
        # ... (_update_height remains the same) ...
        if not self.is_mounted:
            return
        required_height = self.wrapped_document.height + 2
        target_height = max(3, required_height)
        if self.styles.height != target_height:
            self.styles.height = target_height

    # --- Event Handlers ---
    def on_mount(self, event: events.Mount) -> None:
        """Called when the widget is mounted."""
        # 1. Call the on_mount method of the class *after* ScrollView in the MRO
        #    This ensures Widget.on_mount (and potentially ScrollableContainer.on_mount)
        #    gets called with the event, handling essential setup.
        #    We target Widget specifically for robustness, as ScrollableContainer might change.
        #super(self).on_mount(self)

        # 2. Manually replicate ScrollView.on_mount logic
        self._refresh_scrollbars()

        # 3. Manually replicate TextArea.on_mount logic
        #    (Copied from Textual source for TextArea._on_mount as of recent versions)
        self.watch(self.app, "theme", self._app_theme_changed, init=False)
        self.blink_timer = self.set_interval(
            0.5,
            self._toggle_cursor_blink_visible,
            pause=not (self.cursor_blink and self.has_focus),
        )

        # 4. Run WrappingInput's specific on_mount logic
        self._update_height()

    def on_resize(self, event: events.Resize) -> None:
        # ... (on_resize remains the same) ...
        super().on_resize(event)
        self._update_height()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        # ... (on_text_area_changed remains the same) ...
        event.stop()
        self._update_height()
        self.refresh()
        if self.text and not self._initial_value_set:
            self._initial_value_set = True

    # --- Action Handlers ---
    def action_submit(self) -> None:
        # ... (action_submit remains the same) ...
        self.post_message(self.Submitted(self, self.text))

    # --- Rendering ---
    def render_line(self, y: int) -> Strip:
        # ... (render_line remains the same, including placeholder logic) ...
        if not self.text and y == 0 and self.placeholder:
            placeholder_text = Text(
                self.placeholder,
                style=self.get_component_rich_style("wrapping-input--placeholder"),
                no_wrap=True,
                overflow="ellipsis"
            )
            strip = placeholder_text.render(self.app.console, self.content_size.width)
            if self.has_focus and self._cursor_visible:
                 cursor_style = self.get_component_rich_style("text-area--cursor")
                 if cursor_style and strip:
                     segments = list(strip)
                     if segments:
                         if segments[0].style:
                             segments[0] = segments[0]._replace(style=segments[0].style + cursor_style)
                         else:
                             segments[0] = segments[0]._replace(style=cursor_style)
                         strip = Strip(segments, strip.cell_length)
                     else:
                         strip = Strip(Text(" ", style=cursor_style).render(self.app.console))
                 else:
                     strip = Strip(Text(" ", style=cursor_style).render(self.app.console))
            strip = strip.pad_right(self.content_size.width)
            return strip.apply_style(self.rich_style)
        else:
            return super().render_line(y)


    # --- Pasting ---
    async def _on_paste(self, event: events.Paste) -> None:
        # ... (_on_paste remains the same) ...
        if self.read_only:
            return
        first_line = event.text.splitlines()[0] if event.text else ""
        if first_line:
            if result := self._replace_via_keyboard(first_line, *self.selection):
                self.move_cursor(result.end_location)
        event.stop()

    # --- Value Property ---
    @property
    def value(self) -> str:
        # ... (value property remains the same) ...
        return self.text

    @value.setter
    def value(self, value: str) -> None:
        # ... (value setter remains the same) ...
        self.load_text(value)
        self.selection = Selection.cursor((self.document.line_count - 1, len(self.document.lines[-1])))
        self._initial_value_set = bool(value)
        self._update_height()
        self.refresh()