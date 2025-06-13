import logging
from typing import Any, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Label, Input

from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.model_widget import ModelWidget
from jrdev.utils.string_utils import is_valid_name, is_valid_cost, is_valid_context_window

logger = logging.getLogger("jrdev")

def _parse_bool(val: str) -> bool:
    true_vals = {"1", "true", "yes", "y", "on"}
    false_vals = {"0", "false", "no", "n", "off"}
    if val.lower() in true_vals:
        return True
    if val.lower() in false_vals:
        return False
    raise ValueError(f"Invalid boolean value: {val}")

class ModelsWidget(Widget):
    """Widget for managing Models (list, add, edit, remove)."""

    DEFAULT_CSS = """
    ModelsWidget {
        align: center middle;
    }

    #models-container {
        width: 100%;
        max-width: 120;
        height: 100%;
        background: $surface;
        border: none;
        padding: 0;
        margin: 0;
        layout: vertical;
    }

    #header {
        dock: top;
        height: 3;
        padding: 0 1;
        border-bottom: solid $accent;
    }

    #header-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #models-list-scrollable-container {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
        overflow-x: hidden;
        scrollbar-background: #1e1e1e;
        scrollbar-background-hover: #1e1e1e;
        scrollbar-background-active: #1e1e1e;
        scrollbar-color: #63f554 30%;
        scrollbar-color-active: #63f554;
        scrollbar-color-hover: #63f554 50%;
        scrollbar-size: 1 1;
        scrollbar-size-horizontal: 1;
    }
    #models-list-content-area {
        width: 100%;
        height: auto;
    }
    .model-section-container, #new-model-form-container {
        border: round $panel;
        padding: 0;
        margin: 0;
        background: $surface-lighten-1;
        height: auto;
    }
    .section-header-label {
        text-style: bold;
        color: #63f554;
        margin-bottom: 1;
        height: auto;
    }
    .detail-row {
        layout: horizontal;
        height: auto;
    }
    .detail-label {
        color: $text-muted;
        border: none;
        height: auto;
    }
    .save-new-button {
        align-horizontal: left;
        margin-right: 1;
    }
    """

    def __init__(self, core_app: Any, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.core_app = core_app
        self.model_widgets = {}  # model_name => widget
        self.model_container = ScrollableContainer(id="models-list-scrollable-container")
        self.create_model_widgets()

    def compose(self) -> ComposeResult:
        with Vertical(id="models-container"):
            with self.model_container:
                with Vertical(id="new-model-form-container"):
                    yield Label("Add New Model", classes="section-header-label")
                    yield Label("Note: Model name must be unique.", classes="detail-label")
                    with Horizontal(classes="detail-row"):
                        yield Label("Name:", classes="detail-label")
                        yield Input(placeholder="e.g., gpt-4", id="new-model-name-input", classes="detail-input", tooltip="Name of the model.")
                    with Horizontal(classes="detail-row"):
                        yield Label("Provider:", classes="detail-label")
                        yield Input(placeholder="e.g., openai", id="new-model-provider-input", classes="detail-input", tooltip="Provider name.")
                    with Horizontal(classes="detail-row"):
                        yield Label("Is Think:", classes="detail-label")
                        yield Input(placeholder="true/false", id="new-model-is-think-input", classes="detail-input", tooltip="Is this a 'think/reasoning' model? Think models have a thinking stage, where output is streamed wrapped in <think></think> tags")
                    with Horizontal(classes="detail-row"):
                        yield Label("Input Cost:", classes="detail-label")
                        yield Input(placeholder="e.g., 10", id="new-model-input-cost-input", classes="detail-input", tooltip="Input cost per million tokens.")
                    with Horizontal(classes="detail-row"):
                        yield Label("Output Cost:", classes="detail-label")
                        yield Input(placeholder="e.g., 20", id="new-model-output-cost-input", classes="detail-input", tooltip="Output cost per million tokens.")
                    with Horizontal(classes="detail-row"):
                        yield Label("Context Tokens:", classes="detail-label")
                        yield Input(placeholder="e.g., 8192", id="new-model-context-tokens-input", classes="detail-input", tooltip="Context window size.")
                    yield Button("Save Model", id="btn-add-new-model-action", classes="save-new-button")

    async def on_mount(self) -> None:
        self.style_input(self.query_one("#new-model-name-input", Input))
        self.style_input(self.query_one("#new-model-provider-input", Input))
        self.style_input(self.query_one("#new-model-is-think-input", Input))
        self.style_input(self.query_one("#new-model-input-cost-input", Input))
        self.style_input(self.query_one("#new-model-output-cost-input", Input))
        self.style_input(self.query_one("#new-model-context-tokens-input", Input))
        # Asynchronously populate the list of models
        await self.populate_models()

    def create_model_widgets(self):
        """Create the model widgets, preparing them for mount when needed"""
        models = self.core_app.get_models()
        for model in models:
            widget = ModelWidget(model)
            self.model_widgets[model["name"]] = widget

    async def populate_models(self) -> None:
        """Load and mount model widgets asynchronously."""
        widgets = []
        for model_name in self.model_widgets.keys():
            widgets.append(self.model_widgets[model_name])

        await self.model_container.mount_all(widgets)

    def style_input(self, input_widget: Input) -> None:
        input_widget.styles.border = "none"
        input_widget.styles.height = 1

    async def handle_models_updated(self) -> None:
        models = self.core_app.get_models()
        # Add new models
        if len(models) > len(self.model_widgets.keys()):
            for model in models:
                if model["name"] not in self.model_widgets.keys():
                    self.model_widgets[model["name"]] = ModelWidget(model)
                    await self.model_container.mount(self.model_widgets[model["name"]])
                    return
        # Remove deleted models
        elif len(models) < len(self.model_widgets.keys()):
            removed_name = None
            model_names = [model["name"] for model in models]
            for model_name in list(self.model_widgets.keys()):
                if model_name not in model_names:
                    removed_name = model_name
                    break
            if removed_name and removed_name in self.model_widgets:
                await self.model_widgets[removed_name].remove()
                self.model_widgets.pop(removed_name)
        else:
            # Model details might have been edited
            app_models_list = self.core_app.get_models()
            for app_model in app_models_list:
                if app_model["name"] in self.model_widgets:
                    widget = self.model_widgets[app_model["name"]]
                    # Check if details have changed
                    if (
                        widget.model.get("provider") != app_model["provider"] or
                        str(widget.model.get("is_think")) != str(app_model.get("is_think")) or
                        str(widget.model.get("input_cost")) != str(app_model.get("input_cost")) or
                        str(widget.model.get("output_cost")) != str(app_model.get("output_cost")) or
                        str(widget.model.get("context_tokens")) != str(app_model.get("context_tokens"))
                    ):
                        await widget.update_model_details(app_model)

    @on(Button.Pressed, "#btn-add-new-model-action")
    def handle_save_pressed(self):
        name_input = self.query_one("#new-model-name-input", Input)
        provider_input = self.query_one("#new-model-provider-input", Input)
        is_think_input = self.query_one("#new-model-is-think-input", Input)
        input_cost_input = self.query_one("#new-model-input-cost-input", Input)
        output_cost_input = self.query_one("#new-model-output-cost-input", Input)
        context_tokens_input = self.query_one("#new-model-context-tokens-input", Input)

        name = name_input.value.strip()
        provider = provider_input.value.strip()
        is_think_str = is_think_input.value.strip()
        input_cost_str = input_cost_input.value.strip()
        output_cost_str = output_cost_input.value.strip()
        context_tokens_str = context_tokens_input.value.strip()

        # Validation (same as /model command handler)
        if not is_valid_name(name):
            self.notify(f"Invalid model name '{name}'. Allowed: 1-64 chars, alphanumeric, underscore, hyphen; no path separators.", timeout=5)
            return
        if not is_valid_name(provider):
            self.notify(f"Invalid provider name '{provider}'. Allowed: 1-64 chars, alphanumeric, underscore, hyphen; no path separators.", timeout=5)
            return
        try:
            is_think = _parse_bool(is_think_str)
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

        # Check for duplicate model name
        if name in self.core_app.get_model_names():
            self.notify(f"A model named '{name}' already exists in your configuration.", timeout=5)
            return

        self.post_message(CommandRequest(f"/model add {name} {provider} {is_think} {input_cost_float} {output_cost_float} {context_tokens}"))
        name_input.value = ""
        provider_input.value = ""
        is_think_input.value = ""
        input_cost_input.value = ""
        output_cost_input.value = ""
        context_tokens_input.value = ""
