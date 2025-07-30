from typing import Any, Optional
from textual import on
from textual.widgets import DataTable, Select, Button, Label
from textual.containers import Horizontal, Vertical, Container
from textual.widget import Widget
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.add_model_modal import AddModelModal
from jrdev.ui.tui.add_provider_modal import AddProviderModal
from jrdev.ui.tui.edit_provider_modal import EditProviderModal
from jrdev.ui.tui.edit_model_modal import EditModelModal


class ManagementWidget(Widget):
    """A widget to manage models and providers."""

    DEFAULT_CSS = """
    ManagementWidget {
        layout: horizontal;
    }

    #left-pane {
        width: 30%;
        padding: 1;
        border-right: solid $primary;
    }

    #right-pane {
        width: 70%;
        padding: 1;
        overflow-x: auto;
    }
    """

    def __init__(self, core_app: Any, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.core_app = core_app

    def on_mount(self):
        """Populate the widgets with data."""
        self.populate_providers()
        self.populate_models()

    def populate_providers(self):
        """Populates the provider select widget."""
        provider_select = self.query_one("#provider-select", Select)
        providers = self.core_app.provider_list()
        provider_options = [("ALL", "all")] + [(provider.name, provider.name) for provider in providers]
        provider_select.set_options(provider_options)

    def populate_models(self, provider_filter: Optional[str] = None):
        """Populates the models table."""
        models_table = self.query_one("#models-table", DataTable)
        models_table.clear()
        models = self.core_app.get_models()
        if not models_table.columns:
            models_table.add_columns("Name", "Provider", "Think", "Input Cost", "Output Cost", "Context", "Edit", "Remove")
        for model in models:
            if provider_filter and provider_filter != "all" and model["provider"] != provider_filter:
                continue
            models_table.add_row(
                model["name"],
                model["provider"],
                str(model.get("is_think", False)),
                str(model.get("input_cost", 0)),
                str(model.get("output_cost", 0)),
                str(model.get("context_tokens", 0)),
                Button("Edit", id=f"edit-model-{self.sanitize_id(model['name'])}"),
                Button("Remove", id=f"remove-model-{self.sanitize_id(model['name'])}")
            )

    def sanitize_id(self, name: str) -> str:
        """Sanitizes a string to be used as a widget ID."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    @on(Select.Changed, "#provider-select")
    def handle_provider_change(self, event: Select.Changed):
        """Handle provider selection changes."""
        self.populate_models(event.value)

    @on(Button.Pressed, "#add-provider")
    def add_provider(self):
        """Add a new provider."""
        self.app.push_screen(AddProviderModal())

    @on(Button.Pressed, "#edit-provider")
    def edit_provider(self):
        """Edit the selected provider."""
        provider_select = self.query_one("#provider-select", Select)
        provider_name = provider_select.value
        if provider_name and provider_name != "all":
            self.app.push_screen(EditProviderModal(provider_name))

    @on(Button.Pressed, "#remove-provider")
    def remove_provider(self):
        """Remove the selected provider."""
        provider_select = self.query_one("#provider-select", Select)
        provider_name = provider_select.value
        if provider_name and provider_name != "all":
            self.post_message(CommandRequest(f"/provider remove {provider_name}"))

    @on(Button.Pressed, "#add-model")
    def add_model(self):
        """Add a new model."""
        self.app.push_screen(AddModelModal())

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses in the widget."""
        if event.button.id.startswith("edit-model-"):
            sanitized_name = event.button.id.replace("edit-model-", "")
            for model in self.core_app.get_models():
                if self.sanitize_id(model['name']) == sanitized_name:
                    self.app.push_screen(EditModelModal(model['name']))
                    return
        elif event.button.id.startswith("remove-model-"):
            sanitized_name = event.button.id.replace("remove-model-", "")
            for model in self.core_app.get_models():
                if self.sanitize_id(model['name']) == sanitized_name:
                    self.post_message(CommandRequest(f"/model remove {model['name']}"))
                    return

    def compose(self):
        """Compose the widget."""
        with Horizontal():
            with Vertical(id="left-pane"):
                yield Label("Providers")
                yield Select([], id="provider-select")
                yield Button("Add Provider", id="add-provider")
                yield Button("Edit Provider", id="edit-provider")
                yield Button("Remove Provider", id="remove-provider")
            with Container(id="right-pane"):
                yield Label("Models")
                yield DataTable(id="models-table")
                yield Button("Add Model", id="add-model")
