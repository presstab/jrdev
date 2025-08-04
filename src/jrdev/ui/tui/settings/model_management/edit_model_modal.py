from textual.widgets import Input, Button, Select
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.settings.model_management.base_model_modal import BaseModelModal


class EditModelModal(BaseModelModal):
    """A modal screen to edit a model, using shared BaseModelModal styling and helpers."""

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name

    def compose(self):
        container, header = self.build_container("edit-model-container", f"Edit {self.model_name}")
        with container:
            yield header
            yield self.labeled_row("Provider", Select([], id="provider-select"))
            yield self.labeled_row("Think?", Input(placeholder="true/false", id="is-think"))
            yield self.labeled_row("Input Cost", Input(placeholder="Input Cost (per 1M tokens)", id="input-cost"))
            yield self.labeled_row("Output Cost", Input(placeholder="Output Cost (per 1M tokens)", id="output-cost"))
            yield self.labeled_row("Ctx Tokens", Input(placeholder="Ctx tokens", id="context-window"))
            yield self.actions_row()

    def on_mount(self):
        """Populate the inputs with the existing data."""
        model = self.app.jrdev.get_model(self.model_name)
        if model:
            provider_select = self.query_one("#provider-select", Select)
            # Populate providers using shared helper
            self.populate_providers(provider_select)
            provider_select.value = model.get("provider")

            # Think flag
            self.query_one("#is-think", Input).value = str(model.get("is_think", False))

            # Costs: stored per 10M -> display per 1M
            input_cost_display = self.stored_to_display_cost(model.get("input_cost", 0))
            output_cost_display = self.stored_to_display_cost(model.get("output_cost", 0))
            self.query_one("#input-cost", Input).value = str(input_cost_display)
            self.query_one("#output-cost", Input).value = str(output_cost_display)

            # Context window
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
                is_think = self.parse_bool(is_think_str)
            except ValueError as e:
                self.app.notify(str(e), severity="error")
                return

            input_cost_display = self.parse_cost_display(input_cost_str_display, "input cost")
            if input_cost_display is None:
                return
            output_cost_display = self.parse_cost_display(output_cost_str_display, "output cost")
            if output_cost_display is None:
                return

            context_window_int = self.parse_context_window(context_window_str)
            if context_window_int is None:
                return

            # Convert per-1M display values to stored per-10M
            input_cost_stored = input_cost_display / 10
            output_cost_stored = output_cost_display / 10

            self.post_message(CommandRequest(f"/model edit {self.model_name} {provider} {is_think} {input_cost_stored} {output_cost_stored} {context_window_int}"))
            self.app.pop_screen()
        else:
            self.app.pop_screen()
