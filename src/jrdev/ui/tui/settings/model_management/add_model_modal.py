from textual.widgets import Input, Button, Select
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.settings.model_management.base_model_modal import BaseModelModal


class AddModelModal(BaseModelModal):
    """A modal screen to add a new model, using shared BaseModelModal styling and helpers."""

    def compose(self):
        container, header = self.build_container("add-model-container", "Add New Model")
        with container:
            yield header
            yield self.labeled_row("Model Name", Input(placeholder="Model Name", id="model-name"))
            yield self.labeled_row("Provider", Select([], id="provider-select"))
            yield self.labeled_row("Think?", Input(placeholder="true/false", id="is-think"))
            yield self.labeled_row("Input Cost", Input(placeholder="Input Cost (per 1M tokens)", id="input-cost"))
            yield self.labeled_row("Output Cost", Input(placeholder="Output Cost (per 1M tokens)", id="output-cost"))
            yield self.labeled_row("Ctx Tokens", Input(placeholder="Ctx tokens", id="context-window"))
            yield self.actions_row()

    def on_mount(self):
        """Populate the provider select."""
        provider_select = self.query_one("#provider-select", Select)
        self.populate_providers(provider_select)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            name = self.query_one("#model-name", Input).value
            provider = self.query_one("#provider-select", Select).value
            is_think_str = self.query_one("#is-think", Input).value
            input_cost_str_display = self.query_one("#input-cost", Input).value
            output_cost_str_display = self.query_one("#output-cost", Input).value
            context_window_str = self.query_one("#context-window", Input).value

            if not self.validate_name(name):
                self.app.notify("Invalid model name", severity="error")
                return
            if not provider or provider is Select.BLANK:
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

            input_cost_stored = input_cost_display / 10
            output_cost_stored = output_cost_display / 10

            self.post_message(CommandRequest(f"/model add {name} {provider} {is_think} {input_cost_stored} {output_cost_stored} {context_window_int}"))
            self.app.pop_screen()
        else:
            self.app.pop_screen()