import os
from collections import deque
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Label
from textual.containers import Container

class LogViewerScreen(Screen):
    """A screen to view the application's log file."""

    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def __init__(self, core_app, **kwargs):
        super().__init__(**kwargs)
        self.core_app = core_app
        self.log_file_path = os.path.expanduser("~/.jrdev/jrdev.log")
        self._lines = deque(maxlen=100)
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="log-viewer-container"):
            yield ListView(id="log-list")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        self.update_logs()
        self._timer = self.set_interval(2, self.update_logs)

    def on_unmount(self) -> None:
        """Called when the screen is unmounted."""
        if self._timer:
            self._timer.stop()

    def update_logs(self) -> None:
        """Read the log file and update the list view."""
        try:
            with open(self.log_file_path, "r") as f:
                # Read all lines and let the deque handle the limit
                self._lines.extend(f.readlines())
        except FileNotFoundError:
            self.query_one("#log-list", ListView).append(
                ListItem(Label(f"Log file not found at {self.log_file_path}"))
            )
            return
        except Exception as e:
            self.query_one("#log-list", ListView).append(
                ListItem(Label(f"Error reading log file: {e}"))
            )
            return

        log_list = self.query_one("#log-list", ListView)
        log_list.clear()
        for line in self._lines:
            log_list.append(ListItem(Label(line.strip())))
        log_list.scroll_end(animate=False)
