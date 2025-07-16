from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal
from typing import Any, Generator, Optional
import asyncio

class CommandConfirmationScreen(ModalScreen[bool]):
    """Modal screen for confirming a terminal command."""

    DEFAULT_CSS = """
    CommandConfirmationScreen {
        align: center middle;
    }

    #command-confirmation-dialog {
        width: 80%;
        max-width: 80;
        height: auto;
        background: $surface;
        border: round $accent;
        padding: 1 2;
        layout: vertical;
    }

    #command-confirmation-dialog > Label {
        margin-bottom: 1;
    }
    
    #command-display {
        background: $surface-darken-1;
        border: round $panel;
        padding: 1;
        width: 100%;
        height: auto;
        max-height: 10;
        overflow-y: auto;
        margin-bottom: 1;
    }

    #command-confirmation-buttons {
        align-horizontal: right;
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    #command-confirmation-buttons > Button {
        margin-left: 2;
    }
    """

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command
        self.future: Optional[asyncio.Future] = None

    def compose(self) -> Generator[Any, None, None]:
        with Vertical(id="command-confirmation-dialog"):
            yield Label("The AI wants to run the following terminal command:")
            with Vertical(id="command-display"):
                yield Label(f"[bold yellow]{self.command}[/bold yellow]", markup=True)
            yield Label("Do you want to allow this?")
            with Horizontal(id="command-confirmation-buttons"):
                yield Button("Yes", id="yes-button", variant="success")
                yield Button("No", id="no-button", variant="error")

    def on_mount(self) -> None:
        self.query_one("#yes-button").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        result = event.button.id == "yes-button"
        if self.future:
            self.future.set_result(result)
        self.dismiss(result)

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts."""
        if event.key.lower() == "y":
            if self.future:
                self.future.set_result(True)
            self.dismiss(True)
        elif event.key.lower() == "n":
            if self.future:
                self.future.set_result(False)
            self.dismiss(False)
