from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, Input

from jrdev.ui.tui.command_request import CommandRequest
from jrdev.utils.string_utils import is_valid_name, is_valid_cost, is_valid_context_window

class ModelWidget(Widget):
    DEFAULT_CSS = """
    ModelWidget {
        margin: 0;
        padding: 0;
        height: auto;
    }
    #model-widget-container {
        border: round $panel;
        padding: 0;
        margin: 0;
        background: $surface-lighten-1;
        height: auto;
    }
    .form-header-label {
        text-style: bold;
        color: #63f554;
        margin-bottom: 1;
        height: auto;
    }
    .form-row {
        layout: horizontal;
        height: auto;
    }
    .form-label {
        color: $text-muted;
        border: none;
        height: auto;
    }
    .action-button {
        align-horizontal: left;
        margin-right: 1;
        margin-top: 1;
    }
    .action-buttons-container {
        align-horizontal: left;
        margin-top: 1;
        height: auto;
    }
    .action-buttons-container Button {
        margin-left: 1;
        border: none;
    }
    .detail-input {
        border: none;
        height: 1;
    }
    .detail-input.selected {
        border: none;
        height: 1;
    }
    """

    def __init__(self, model: dict):
        super().__init__()
        self.model = model.copy()
        self.edit_mode = False
        self.btn_edit = Button("Edit", id="btn-edit", variant="success", classes="action-button")
        self.btn_remove = Button("Remove", id="btn-remove", variant="success", classes="action-button")
        self.btn_save = Button("Save Edits", id="btn-save", variant="success", classes="action-button")
        self.btn_cancel = Button("Cancel", id="btn-cancel", variant="success", classes="action-button")
        self.btn_save.display = False
        self.btn_cancel.display = False
        self.btn_confirm_remove = Button("Confirm Removal", id="btn-confirm-remove", variant="error", classes="action-button")
        self.btn_cancel_remove = Button("Cancel", id="btn-cancel-remove", variant="error", classes="action-button")
        self.btn_confirm_remove.display = False
        self.btn_cancel_remove.display = False
        self.input_provider = Input(value=f"{self.model['provider']}", id="input-provider", classes="detail-input", disabled=True, tooltip="Provider name.")
        self.input_is_think = Input(value=str(self.model.get('is_think', False)), id="input-is-think", classes="detail-input", disabled=True, tooltip="Is this a 'think' model?")

        # cost is stored internally as per 10m tokens
        input_cost = self.model.get('input_cost', 0)
        if input_cost:
            input_cost = input_cost / 10
        output_cost = self.model.get('output_cost', 0)
        if output_cost:
            output_cost = output_cost / 10

        self.input_input_cost = Input(value=str(input_cost), id="input-input-cost", classes="detail-input", disabled=True, tooltip="Input cost.")
        self.input_output_cost = Input(value=str(output_cost), id="input-output-cost", classes="detail-input", disabled=True, tooltip="Output cost.")
        self.input_context_tokens = Input(value=str(self.model.get('context_tokens', 0)), id="input-context-tokens", classes="detail-input", disabled=True, tooltip="Context window size.")

    def compose(self) -> ComposeResult:
        with Vertical(id="model-widget-container"):
            yield Label(f"{self.model['name']}", classes="form-header-label")
            with Horizontal(classes="form-row"):
                yield Label("Provider:", classes="form-label")
                yield self.input_provider
            with Horizontal(classes="form-row"):
                yield Label("Is Think:", classes="form-label")
                yield self.input_is_think
            with Horizontal(classes="form-row"):
                yield Label("Input Cost:", classes="form-label")
                yield self.input_input_cost
            with Horizontal(classes="form-row"):
                yield Label("Output Cost:", classes="form-label")
                yield self.input_output_cost
            with Horizontal(classes="form-row"):
                yield Label("Context Tokens:", classes="form-label")
                yield self.input_context_tokens
            with Horizontal(classes="form-row"):
                yield self.btn_edit
                yield self.btn_remove
                yield self.btn_confirm_remove
                yield self.btn_cancel_remove
                yield self.btn_save
                yield self.btn_cancel

    async def on_mount(self) -> None:
        self.style_input(self.input_provider)
        self.style_input(self.input_is_think)
        self.style_input(self.input_input_cost)
        self.style_input(self.input_output_cost)
        self.style_input(self.input_context_tokens)

    def style_input(self, input_widget: Input) -> None:
        input_widget.styles.border = "none"
        input_widget.styles.height = 1
        pass

    def set_edit_mode(self, is_edit_mode: bool) -> None:
        self.edit_mode = is_edit_mode
        for field in ["#input-provider", "#input-is-think", "#input-input-cost", "#input-output-cost", "#input-context-tokens"]:
            input_widget = self.query_one(field, Input)
            input_widget.disabled = not is_edit_mode
        self.btn_edit.display = not is_edit_mode
        self.btn_remove.display = not is_edit_mode
        self.btn_save.display = is_edit_mode
        self.btn_cancel.display = is_edit_mode

    async def update_model_details(self, new_model: dict) -> None:
        self.model = new_model.copy()
        self.query_one(".form-header-label", Label).update(new_model["name"])
        self.query_one("#input-provider", Input).value = new_model["provider"]
        self.query_one("#input-is-think", Input).value = str(new_model.get("is_think", False))
        input_cost = new_model.get("input_cost", 0)
        output_cost = new_model.get("output_cost", 0)
        # value is stored internally as cost per 10m tokens, convert to per 1m
        if input_cost:
            input_cost = input_cost / 10
        if output_cost:
            output_cost = output_cost / 10

        self.query_one("#input-input-cost", Input).value = str(input_cost)
        self.query_one("#input-output-cost", Input).value = str(output_cost)
        self.query_one("#input-context-tokens", Input).value = str(new_model.get("context_tokens", 0))

    @on(Button.Pressed, "#btn-edit")
    async def handle_edit_clicked(self, event: Button.Pressed) -> None:
        self.set_edit_mode(True)

    @on(Button.Pressed, "#btn-remove")
    async def handle_remove_clicked(self, event: Button.Pressed) -> None:
        self.btn_edit.display = False
        self.btn_remove.display = False
        self.btn_confirm_remove.display = True
        self.btn_cancel_remove.display = True

    @on(Button.Pressed, "#btn-confirm-remove")
    async def handle_confirm_remove(self, event: Button.Pressed) -> None:
        self.post_message(CommandRequest(f"/model remove {self.model['name']}"))
        self.btn_confirm_remove.display = False
        self.btn_cancel_remove.display = False
        self.btn_edit.display = True
        self.btn_remove.display = True

    @on(Button.Pressed, "#btn-cancel-remove")
    async def handle_cancel_remove(self, event: Button.Pressed) -> None:
        self.btn_confirm_remove.display = False
        self.btn_cancel_remove.display = False
        self.btn_edit.display = True
        self.btn_remove.display = True

    @on(Button.Pressed, "#btn-cancel")
    async def handle_cancel_clicked(self, event: Button.Pressed) -> None:
        self.set_edit_mode(False)

    def _parse_bool(self, val: str) -> bool:
        true_vals = {"1", "true", "yes", "y", "on"}
        false_vals = {"0", "false", "no", "n", "off"}
        if val.lower() in true_vals:
            return True
        if val.lower() in false_vals:
            return False
        raise ValueError(f"Invalid boolean value: {val}")

    @on(Button.Pressed, "#btn-save")
    async def handle_save_clicked(self, event: Button.Pressed) -> None:
        provider = self.query_one("#input-provider", Input).value.strip()
        is_think_str = self.query_one("#input-is-think", Input).value.strip()
        input_cost_str = self.query_one("#input-input-cost", Input).value.strip()
        output_cost_str = self.query_one("#input-output-cost", Input).value.strip()
        context_tokens_str = self.query_one("#input-context-tokens", Input).value.strip()
        name = self.model["name"]

        # Validation (same as /model command handler)
        if not is_valid_name(name):
            self.notify(f"Invalid model name '{name}'. Allowed: 1-64 chars, alphanumeric, underscore, hyphen", timeout=5)
            return
        if not is_valid_name(provider):
            self.notify(f"Invalid provider name '{provider}'. Allowed: 1-64 chars, alphanumeric, underscore, hyphen.", timeout=5)
            return
        try:
            is_think = self._parse_bool(is_think_str)
        except Exception as e:
            self.notify(f"Invalid value for is_think: {e}", timeout=5)
            return
        try:
            input_cost_float = float(input_cost_str)
        except Exception:
            self.notify(f"Invalid value for input_cost: '{input_cost_str}' (must be a float)", timeout=5)
            return
        if not is_valid_cost(input_cost_float):
            self.notify("input_cost must be between 0 and 1000 (dollars per 1,000,000 tokens).", timeout=5)
            return
        try:
            output_cost_float = float(output_cost_str)
        except Exception:
            self.notify(f"Invalid value for output_cost: '{output_cost_str}' (must be a float)", timeout=5)
            return
        if not is_valid_cost(output_cost_float):
            self.notify("output_cost must be between 0 and 1000 (dollars per 1,000,000 tokens).", timeout=5)
            return
        try:
            context_tokens = int(context_tokens_str)
        except Exception:
            self.notify(f"Invalid value for context_tokens: '{context_tokens_str}' (must be integer)", timeout=5)
            return
        if not is_valid_context_window(context_tokens):
            self.notify("context_tokens must be between 1 and 1,000,000,000.", timeout=5)
            return

        self.post_message(CommandRequest(f"/model edit {name} {provider} {is_think} {input_cost_float} {output_cost_float} {context_tokens}"))
        self.set_edit_mode(False)
