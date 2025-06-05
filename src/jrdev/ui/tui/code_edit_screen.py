from typing import List, Optional, Generator, Any
import asyncio

from textual.screen import ModalScreen
from textual.widgets import Label, Button, TextArea
from textual.containers import Vertical, Horizontal

class CodeEditScreen(ModalScreen[Optional[List[str]]]):
    """A modal screen for editing text content, typically a file with diff markers."""

    DEFAULT_CSS = """
    CodeEditScreen {
        align: center middle;
    }

    #code-edit-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: round $accent;
        padding: 1;
        layout: vertical;
    }

    #code-edit-header {
        height: auto;
        padding: 0 1;
        border-bottom: solid $accent;
        margin-bottom: 1;
    }

    #code-edit-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #code-edit-textarea {
        height: 1fr; /* Take remaining space */
        border: round $panel;
    }

    #code-edit-footer {
        height: 3;
        padding-top: 1;
        border-top: solid $accent;
        align: left middle; /* Align buttons to the left */
    }

    #code-edit-footer Button {
        margin-left: 1;
    }
    """

    def __init__(
        self,
        content_lines: List[str],
        prompt_message: str,
        future: asyncio.Future[Optional[List[str]]],
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.content_lines = content_lines
        self.prompt_message = prompt_message
        self.future = future

    def compose(self) -> Generator[Any, None, None]:
        with Vertical(id="code-edit-container"):
            with Horizontal(id="code-edit-header"):
                yield Label(self.prompt_message, id="code-edit-title")
            yield TextArea(
                "\n".join(self.content_lines),
                id="code-edit-textarea",
                show_line_numbers=True
            )
            with Horizontal(id="code-edit-footer"):
                yield Button("Save", id="save-button", variant="success")
                yield Button("Cancel", id="cancel-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-button":
            edited_text = self.query_one("#code-edit-textarea", TextArea).text
            # Textarea.text joins lines with \n, so splitting by \n is correct.
            edited_lines = edited_text.splitlines()
            self.future.set_result(edited_lines)
            self.dismiss(edited_lines)
        elif event.button.id == "cancel-button":
            self.future.set_result(None)  # Indicate cancellation
            self.dismiss(None)
