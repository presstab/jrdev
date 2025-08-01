from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Select
from textual.containers import Vertical
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.utils.string_utils import is_valid_name, is_valid_cost, is_valid_context_window


def _parse_bool(val: str) -> bool:
    true_vals = {"1", "true", "yes", "y", "on"}
    false_vals = {"0", "false", "no", "n", "off"}
    if val.lower() in true_vals:
        return True
    if val.lower() in false_vals:
        return False
    raise ValueError(f"Invalid boolean value: {val}")


class EditModelModal(ModalScreen):
    """A modal screen to edit a model."""

    DEFAULT_CSS = """
    EditModelModal {
        align: center middle;
        background: transparent;
    }
    #edit-model-container {
        width: 28;
        min-width: 24;
        max-width: 32;
        height: auto;
        padding: 0 1;
        margin: 0;
        align: center middle;
        border: round #2a2a2a;
        background: #1e1e1e 80%;
        overflow: hidden;
        content-align: center middle;
    }
    #edit-model-container > Label {
        padding: 0;
        margin: 0 0 1 0;
    }
    #edit-model-container > Input,
    #edit-model-container > Select,
    #edit-model-container > Button {
        height: 1;
        margin: 0;
    }
    """

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name

    def compose(self):
        with Vertical(id="edit-model-container"):
            yield Label(f"Edit {self.model_name}")
            yield Select([], id="provider-select")
            yield Input(placeholder="Think? (true/false)", id="is-think")
            yield Input(placeholder="In cost", id="input-cost")
            yield Input(placeholder="Out cost", id="output-cost")
            yield Input(placeholder="Ctx tokens", id="context-window")
            yield Button("Save", id="save")
            yield Button("Cancel", id="cancel")

    def on_mount(self):
        """Populate the inputs with the existing data."""
        model = self.app.jrdev.get_model(self.model_name)
        if model:
            provider_select = self.query_one("#provider-select", Select)
            providers = self.app.jrdev.provider_list()
            provider_options = [(provider.name, provider.name) for provider in providers]
            provider_select.set_options(provider_options)
            provider_select.value = model["provider"]
            self.query_one("#is-think", Input).value = str(model.get("is_think", False))
            self.query_one("#input-cost", Input).value = str(model.get("input_cost", 0))
            self.query_one("#output-cost", Input).value = str(model.get("output_cost", 0))
            self.query_one("#context-window", Input).value = str(model.get("context_tokens", 0))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            provider = self.query_one("#provider-select", Select).value
            is_think_str = self.query_one("#is-think", Input).value
            input_cost_str = self.query_one("#input-cost", Input).value
            output_cost_str = self.query_one("#output-cost", Input).value
            context_window_str = self.query_one("#context-window", Input).value

            if not provider:
                self.app.notify("Provider is required", severity="error")
                return
            try:
                is_think = _parse_bool(is_think_str)
            except ValueError as e:
                self.app.notify(str(e), severity="error")
                return
            if not is_valid_cost(float(input_cost_str)):
                self.app.notify("Invalid input cost", severity="error")
                return
            if not is_valid_cost(float(output_cost_str)):
                self.app.notify("Invalid output cost", severity="error")
                return
            if not is_valid_context_window(int(context_window_str)):
                self.app.notify("Invalid context window", severity="error")
                return

            self.post_message(CommandRequest(f"/model edit {self.model_name} {provider} {is_think} {input_cost_str} {output_cost_str} {context_window_str}"))
            self.app.pop_screen()
        else:
            self.app.pop_screen()
