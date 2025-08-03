from textual.widgets import Button, Label
from textual.containers import Vertical, Horizontal
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.base_model_modal import BaseModelModal


class RemoveModelModal(BaseModelModal):
    """A modal screen to confirm model removal, using shared BaseModelModal styling."""

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name

    def compose(self):
        container, header = self.build_container("remove-model-container", f"Remove {self.model_name}")
        with container:
            yield header
            yield Label(f"Are you sure you want to remove the model '{self.model_name}'?", classes="form-row")
            yield self.actions_row()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            self.post_message(CommandRequest(f"/model remove {self.model_name}"))
        self.app.pop_screen()

    def actions_row(self) -> Horizontal:
        """Return a row with Remove and Cancel buttons."""
        return Horizontal(
            Button("Remove", id="save"),
            Button("Cancel", id="cancel"),
            classes="form-actions"
        )