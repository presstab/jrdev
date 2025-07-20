from textual.widgets import ListView, ListItem
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

class AutocompletePopup(Widget):
    """A widget to display autocomplete suggestions."""

    DEFAULT_CSS = """
    AutocompletePopup {
        layer: tooltips;
        width: 50%;
        height: auto;
        background: $surface;
        border: round $primary;
        display: none;
    }
    """

    def __init__(self, commands: list[str], **kwargs):
        super().__init__(**kwargs)
        self._commands = commands
        self._list_view = ListView(*[ListItem(Static(cmd)) for cmd in self._commands])

    def compose(self) -> ComposeResult:
        with Vertical():
            yield self._list_view

    def update_suggestions(self, suggestions: list[str]):
        """Update the list of suggestions."""
        self._list_view.clear()
        self._list_view.extend([ListItem(Static(cmd)) for cmd in suggestions])
        self.display = bool(suggestions)

    def select_next(self):
        """Select the next item in the list."""
        self._list_view.action_cursor_down()

    def select_previous(self):
        """Select the previous item in the list."""
        self._list_view.action_cursor_up()

    def get_selected_command(self) -> str | None:
        """Get the currently selected command."""
        highlighted = self._list_view.highlighted_child
        if highlighted:
            return highlighted.query_one(Static).renderable
        return None
