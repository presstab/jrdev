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

class AddModelModal(ModalScreen):
    """A modal screen to add a new model."""

    DEFAULT_CSS = """
    AddModelModal {
        align: center middle;
    }

    #add-model-container {
        width: 50;
        height: auto;
        padding: 1 2;
        border: round #2a2a2a;
        background: #1e1e1e;
        gap: 1;
    }
    """

    def compose(self):
        with Vertical(id="add-model-container"):
            yield Label("Add New Model")
            yield Input(placeholder="Model Name", id="model-name")
            yield Select([], id="provider-select")
            yield Input(placeholder="Is Think (true/false)", id="is-think")
            # Display and accept costs per 1M tokens
            yield Input(placeholder="Input Cost (per 1M tokens)", id="input-cost")
            yield Input(placeholder="Output Cost (per 1M tokens)", id="output-cost")
            yield Input(placeholder="Context Window", id="context-window")
            yield Button("Save", id="save")
            yield Button("Cancel", id="cancel")

    def on_mount(self):
        """Populate the provider select."""
        provider_select = self.query_one("#provider-select", Select)
        providers = self.app.jrdev.provider_list()
        provider_options = [(provider.name, provider.name) for provider in providers]
        provider_select.set_options(provider_options)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            name = self.query_one("#model-name", Input).value
            provider = self.query_one("#provider-select", Select).value
            is_think_str = self.query_one("#is-think", Input).value
            input_cost_str_display = self.query_one("#input-cost", Input).value
            output_cost_str_display = self.query_one("#output-cost", Input).value
            context_window_str = self.query_one("#context-window", Input).value

            if not is_valid_name(name):
                self.app.notify("Invalid model name", severity="error")
                return
            if not provider:
                self.app.notify("Provider is required", severity="error")
                return
            try:
                is_think = _parse_bool(is_think_str)
            except ValueError as e:
                self.app.notify(str(e), severity="error")
                return

            # Validate display values (per 1M tokens), then convert to stored units (per 10M tokens)
            try:
                input_cost_display = float(input_cost_str_display)
            except (TypeError, ValueError):
                self.app.notify("Invalid input cost (per 1M tokens)", severity="error")
                return
            try:
                output_cost_display = float(output_cost_str_display)
            except (TypeError, ValueError):
                self.app.notify("Invalid output cost (per 1M tokens)", severity="error")
                return

            # Ensure the per-1M values are within acceptable bounds
            if not is_valid_cost(input_cost_display):
                self.app.notify("Invalid input cost (per 1M tokens)", severity="error")
                return
            if not is_valid_cost(output_cost_display):
                self.app.notify("Invalid output cost (per 1M tokens)", severity="error")
                return

            # Context window validation
            try:
                context_window_int = int(context_window_str)
            except (TypeError, ValueError):
                self.app.notify("Invalid context window", severity="error")
                return
            if not is_valid_context_window(context_window_int):
                self.app.notify("Invalid context window", severity="error")
                return

            # Convert display (per 1M) to stored (per 10M) by multiplying by 10
            input_cost_stored = input_cost_display * 10
            output_cost_stored = output_cost_display * 10

            self.post_message(CommandRequest(f"/model add {name} {provider} {is_think} {input_cost_stored} {output_cost_stored} {context_window_int}"))
            self.app.pop_screen()
        else:
            self.app.pop_screen()
