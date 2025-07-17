import math

from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, RichLog
from textual.containers import Horizontal, VerticalScroll
from typing import Optional
import asyncio

class CommandConfirmationWidget(Widget):
    """Modal screen for confirming a terminal command."""

    DEFAULT_CSS = """
    CommandConfirmationWidget {
        width: 100%;
        height: auto;
        max-height: 15;
    }

    #vlayout_main {
        width: 100%;
        height: auto;
        background: $surface;
        border: none;
        padding: 0;
        margin: 0;
        overflow-y: auto;
    }

    #command-confirmation-buttons {
        border: none;
        align-horizontal: left;
        width: 100%;
        height: 1;
        margin: 1 0 0 0;
    }

    #command-confirmation-buttons > Button {
        margin-left: 2;
    }

    #richlog-confirmation {
        border: none;
        margin: 0;
        padding: 0;
        overflow-y: auto;
    }
    """

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command
        self.future: Optional[asyncio.Future] = None
        self.richlog = RichLog(id="richlog-confirmation", markup=True, wrap=True)

    def compose(self):
        with VerticalScroll(id="vlayout_main"):
            yield self.richlog
            with Horizontal(id="command-confirmation-buttons"):
                yield Button("Yes", id="yes-button", variant="success")
                yield Button("No", id="no-button", variant="error")

    def on_mount(self) -> None:
        self.query_one("#yes-button").focus()
        line_width = max(1, self.parent.parent.virtual_size.width - 3)
        self.richlog.write("[bold]JrDev is requesting to run the following shell command:[/bold]", line_width)
        self.richlog.write(f"[bold yellow]{self.command}[/bold yellow]", line_width)
        self.richlog.write("Do you want to allow this?", line_width)

        # manually set max heights based on line wrapping
        chars = len(self.command)
        wrapped_lines = math.ceil(float(chars) / float(line_width))
        rl_height = wrapped_lines + 2
        self.richlog.styles.max_height = rl_height
        self.parent.styles.max_height = rl_height + 4

    class Result(Message):
        """Send User Click Result"""
        def __init__(self, allow: bool):
            super().__init__()
            self.allow = allow

    def on_button_pressed(self, event: Button.Pressed) -> None:
        result = event.button.id == "yes-button"
        self.post_message(CommandConfirmationWidget.Result(result))

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts."""
        if event.key.lower() == "y":
            self.post_message(CommandConfirmationWidget.Result(True))

        elif event.key.lower() == "n":
            self.post_message(CommandConfirmationWidget.Result(False))
