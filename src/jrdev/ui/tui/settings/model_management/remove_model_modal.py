from textual.widgets import Button, Label
from textual.containers import Horizontal
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.settings.model_management.base_model_modal import BaseModelModal


class RemoveResourceModal(BaseModelModal):
    """A modal screen to confirm resource removal, using shared BaseModelModal styling."""

    def __init__(self, resource_name: str, resource_type: str = "model") -> None:
        super().__init__()
        self.resource_name = resource_name
        self.resource_type = resource_type

    def compose(self):
        container, header = self.build_container("remove-resource-container", f"Remove {self.resource_name}")
        with container:
            yield header
            yield Label(f"Are you sure you want to remove the {self.resource_type} '{self.resource_name}'?", classes="form-row")
            yield self.actions_row()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            if self.resource_type == "model":
                self.post_message(CommandRequest(f"/model remove {self.resource_name}"))
            elif self.resource_type == "provider":
                self.post_message(CommandRequest(f"/provider remove {self.resource_name}"))
        self.app.pop_screen()

    def actions_row(self) -> Horizontal:
        """Return a row with Remove and Cancel buttons."""
        return Horizontal(
            Button("Remove", id="save"),
            Button("Cancel", id="cancel"),
            classes="form-actions"
        )