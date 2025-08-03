from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Select
from textual.containers import Vertical, Horizontal
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
        width: 50%;
        min-width: 24;
        height: 50%;
        padding: 1;
        margin: 0;
        align: center middle;
        border: round $accent;
        background: #1e1e1e 80%;
        overflow: hidden;
        content-align: center middle;
    }
    #edit-model-container > Label {
        padding: 0;
        margin: 0 0 1 0;
    }

    /* Form row styling */
    .form-row {
        layout: horizontal;
        width: 100%;
        height: 3;
        align-vertical: bottom;
        padding: 0 0 0 1;
        background: #1e1e1e 80%;
    }

    .form-row > .form-label {
        width: 20;
        min-width: 16;
        text-align: left;
        color: $text;
    }

    .form-row > Input {
        width: 1fr;
        height: 3;
        border: round $accent;
    }

    #provider-select {
        height: 3;
        width: 1fr;
        max-width: 80;
        border: round $accent;
        margin: 0;
        padding: 0;
        & > SelectCurrent {
            border: none;
            background-tint: $foreground 5%;
        }
        & > SelectOverlay {
            width: 1fr;
            display: none;
            height: auto;
            max-height: 12;
            overlay: screen;
            constrain: none inside;
            color: $foreground;
            border: tall $border-blurred;
            background: $surface;
            &:focus {
                background-tint: $foreground 5%;
            }
            & > .option-list--option {
                padding: 0 1;
            }
        }
        &.-expanded {
            .down-arrow {
                display: none;
            }
            .up-arrow {
                display: block;
            }
            & > SelectOverlay {
                display: block;
            }
        }
    }
    
    #edit-model-container > Input,
    #edit-model-container > Button {
        height: 1;
        margin: 0;
    }

    /* Action buttons row */
    .form-actions {
        layout: horizontal;
        width: 100%;
        height: auto;
        align: center middle;
        padding-top: 1;
        padding-left: 1;
    }

    .form-actions > Button#save,
    .form-actions > Button#cancel {
        width: 1fr;
        height: 1;
    }
    """

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name

    def compose(self):
        with Vertical(id="edit-model-container"):
            yield Label(f"Edit {self.model_name}")
            with Horizontal(classes="form-row"):
                yield Label("Provider", classes="form-label")
                yield Select([], id="provider-select")
            with Horizontal(classes="form-row"):
                yield Label("Think?", classes="form-label")
                yield Input(placeholder="true/false", id="is-think")
            with Horizontal(classes="form-row"):
                yield Label("Input Cost", classes="form-label")
                yield Input(placeholder="Input Cost (per 1M tokens)", id="input-cost")
            with Horizontal(classes="form-row"):
                yield Label("Output Cost", classes="form-label")
                yield Input(placeholder="Output Cost (per 1M tokens)", id="output-cost")
            with Horizontal(classes="form-row"):
                yield Label("Ctx Tokens", classes="form-label")
                yield Input(placeholder="Ctx tokens", id="context-window")
            with Horizontal(classes="form-actions"):
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

            # Stored values are per 10M tokens; convert to display per 1M tokens by dividing by 10
            try:
                input_cost_stored = float(model.get("input_cost", 0))
            except (TypeError, ValueError):
                input_cost_stored = 0.0
            try:
                output_cost_stored = float(model.get("output_cost", 0))
            except (TypeError, ValueError):
                output_cost_stored = 0.0

            input_cost_display = input_cost_stored / 10.0
            output_cost_display = output_cost_stored / 10.0

            self.query_one("#input-cost", Input).value = str(input_cost_display)
            self.query_one("#output-cost", Input).value = str(output_cost_display)
            self.query_one("#context-window", Input).value = str(model.get("context_tokens", 0))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            provider = self.query_one("#provider-select", Select).value
            is_think_str = self.query_one("#is-think", Input).value
            input_cost_str_display = self.query_one("#input-cost", Input).value
            output_cost_str_display = self.query_one("#output-cost", Input).value
            context_window_str = self.query_one("#context-window", Input).value

            if not provider:
                self.app.notify("Provider is required", severity="error")
                return
            try:
                is_think = _parse_bool(is_think_str)
            except ValueError as e:
                self.app.notify(str(e), severity="error")
                return

            # Validate display values (per 1M tokens)
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

            # Convert per-1M display values to stored per-10M by multiplying by 10
            input_cost_stored = input_cost_display * 10.0
            output_cost_stored = output_cost_display * 10.0

            self.post_message(CommandRequest(f"/model edit {self.model_name} {provider} {is_think} {input_cost_stored} {output_cost_stored} {context_window_int}"))
            self.app.pop_screen()
        else:
            self.app.pop_screen()
