from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, Static

class YesNoScreen(ModalScreen[bool]):
    """Screen with a dialog to with yes/no confirmation."""

    def __init__(self, text_prompt: str):
        super().__init__()
        self.text_prompt = text_prompt

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.text_prompt, id="prompt")
            # Add vertical spacing between prompt and buttons
            spacer = Static()
            spacer.styles.height = 1  # 1 row of vertical space
            yield spacer
            with Horizontal():
                yield Button("Confirm", variant="primary", id="confirm")
                yield Button("Cancel", variant="error", id="cancel")
            spacer2 = Static()
            spacer2.styles.height = "1fr"
            yield spacer2

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)
