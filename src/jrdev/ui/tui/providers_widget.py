import logging
from typing import Any, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Label, Input, Static

from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.provider_widget import ProviderWidget
from jrdev.ui.tui.api_key_entry import ApiKeyEntry

from jrdev.utils.string_utils import is_valid_name, is_valid_env_key, is_valid_url

logger = logging.getLogger("jrdev")

class ProvidersWidget(Widget):
    """Widget for managing API Providers (list, add, edit, remove)."""

    DEFAULT_CSS = """
    ProvidersWidget {
        align: center middle;
    }

    #providers-container {
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

    #providers-list-scrollable-container {
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
    
    #providers-list-content-area {
        width: 100%;
        height: auto;
    }

    .provider-section-container, #new-provider-form-container {
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
        self.provider_widgets = {} # provider_name => widget
        self.create_provider_widgets()
        self.provider_container = ScrollableContainer(id="providers-list-scrollable-container")

    def compose(self) -> ComposeResult:
        with Vertical(id="providers-container"):
            with self.provider_container:
                with Vertical(id="new-provider-form-container"):
                    # Create "Add Provider" Form
                    yield Label("Add New Provider", classes="section-header-label")
                    yield Label("Note: A valid API key must be entered after adding a new provider.", classes="detail-label")
                    with Horizontal(classes="detail-row"):
                        yield Label("Name:", classes="detail-label")
                        yield Input(placeholder="e.g., openai_new", id="new-provider-name-input", classes="detail-input", tooltip="Name of the provider, used to reference it.")
                    with Horizontal(classes="detail-row"):
                        yield Label("Base URL:", classes="detail-label")
                        yield Input(placeholder="API URL", id="new-provider-baseurl-input", classes="detail-input", tooltip="Base URL of the API provider.")
                    with Horizontal(classes="detail-row"):
                        yield Label("Env Key:", classes="detail-label")
                        yield Input(placeholder="e.g., OPENAI_API_KEY_NEW", id="new-provider-envkey-input", classes="detail-input", tooltip="Name of the environment variable that holds the API key, not the API key itself.")
                    yield Button("Save Provider", id="btn-add-new-provider-action", classes="save-new-button")

    async def on_mount(self) -> None:
        self.style_input(self.query_one("#new-provider-name-input", Input))
        self.style_input(self.query_one("#new-provider-envkey-input", Input))
        self.style_input(self.query_one("#new-provider-baseurl-input", Input))
        # Asynchronously populate the list of providers
        await self.populate_providers()

    def create_provider_widgets(self):
        """Create provider widgets, preparing them to be mounted when needed"""
        providers = self.core_app.provider_list()
        for provider in providers:
            widget = ProviderWidget(provider.name, provider.base_url, provider.env_key)
            self.provider_widgets[provider.name] = widget

    async def populate_providers(self) -> None:
        """Load and mount provider widgets asynchronously."""
        widgets = []
        for provider_name in self.provider_widgets:
            widgets.append(self.provider_widgets[provider_name])
        await self.provider_container.mount_all(widgets)

    def style_input(self, input_widget: Input) -> None:
        input_widget.styles.border = "none"
        input_widget.styles.height = 1

    async def handle_providers_updated(self) -> None:
        providers = self.core_app.provider_list()
        if len(providers) > len(self.provider_widgets.keys()):
            # provider has been added
            for provider in providers:
                if provider.name not in self.provider_widgets.keys():
                    self.provider_widgets[provider.name] = ProviderWidget(provider.name, provider.base_url, provider.env_key)
                    await self.provider_container.mount(self.provider_widgets[provider.name])
                    return
        elif len(providers) < len(self.provider_widgets.keys()):
            # provider has been removed
            removed_name = None
            provider_names = [provider.name for provider in providers]
            for provider_name in list(self.provider_widgets.keys()):
                if provider_name not in provider_names:
                    removed_name = provider_name
                    break
            if removed_name and removed_name in self.provider_widgets:
                await self.provider_widgets[removed_name].remove()
                self.provider_widgets.pop(removed_name)
        else:
            # Provider details might have been edited
            app_providers_list = self.core_app.provider_list()
            for app_provider in app_providers_list:
                if app_provider.name in self.provider_widgets:
                    widget = self.provider_widgets[app_provider.name]
                    if widget.base_url != app_provider.base_url or \
                       widget.env_key != app_provider.env_key:
                        await widget.update_provider_details(app_provider.name, app_provider.base_url, app_provider.env_key)

    @on(Button.Pressed, "#btn-add-new-provider-action")
    def handle_save_pressed(self):
        name_input = self.query_one("#new-provider-name-input", Input)
        env_key_input = self.query_one("#new-provider-envkey-input", Input)
        base_url_input = self.query_one("#new-provider-baseurl-input", Input)

        name = name_input.value
        env_key_name = env_key_input.value
        base_url = base_url_input.value

        # Validate inputs using the same logic as the command handler
        if not is_valid_name(name):
            self.notify(
                "Invalid provider name. Allowed: 1-64 chars, alphanumeric, underscore, hyphen; no path separators.",
                timeout=5,
                severity="error"
            )
            return
        if not is_valid_env_key(env_key_name):
            self.notify(
                "Invalid env_key. Allowed: 1-128 chars, alphanumeric, underscore, hyphen; no path separators.",
                timeout=5,
                severity="error"
            )
            return
        if not is_valid_url(base_url):
            self.notify(
                "Invalid base_url. Must be a valid http(s) URL.",
                timeout=5,
                severity="error"
            )
            return

        # Send command to core app to add a new provider
        self.post_message(CommandRequest(f"/provider add {name} {env_key_name} {base_url}"))

        # Clear form
        name_input.value = ""
        env_key_input.value = ""
        base_url_input.value = ""
