import logging
from typing import Any, Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Static

from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.provider_widget import ProviderWidget

logger = logging.getLogger("jrdev")

class ProvidersScreen(ModalScreen[bool]):
    """Modal screen for managing API Providers."""

    DEFAULT_CSS = """
    ProvidersScreen {
        align: center middle;
    }

    #providers-container {
        width: 90%;
        max-width: 120; /* Max width for better readability */
        height: 90%;
        background: $surface;
        border: round $accent;
        padding: 0;
        margin: 0;
        layout: vertical;
    }

    #header {
        dock: top;
        height: 3;
        padding: 0 1; /* Added padding for consistency */
        border-bottom: solid $accent;
    }

    #header-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #providers-list-scrollable-container { /* Renamed for clarity */
        height: 1fr; /* Takes remaining space */
        padding: 1;
        overflow-y: auto;
        overflow-x: hidden; /* Prevent horizontal scroll */
    }
    
    #providers-list-content-area { /* Inner container for actual content */
        width: 100%;
        height: auto; /* Grows with content */
    }

    .provider-section-container, #new-provider-form-container {
        border: round $panel;
        padding: 0;
        margin: 0;
        background: $surface-lighten-1;
        height: auto;
    }

    .section-header-label { /* General header for provider or 'Add New' */
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

    #footer {
        dock: bottom;
        height: 3;
        padding: 0 1;
        border-top: solid $accent;
        align: left middle; /* Align buttons to the left */
    }

    #footer Button {
        margin-right: 1; /* Add margin to the right of buttons */
        border: none;
    }
    """

    BINDINGS = [
        Binding("escape", "close_screen", "Close", show=False),
    ]

    def __init__(self, core_app: Any, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.core_app = core_app
        self.provider_widgets = {} # provider_name => widget
        self.provider_container = ScrollableContainer(id="providers-list-scrollable-container")

    def compose(self) -> ComposeResult:
        with Vertical(id="providers-container"):
            with Horizontal(id="header"):
                yield Label("API Providers Management", id="header-title")

            with self.provider_container:
                with Vertical(id="new-provider-form-container"):
                    # Create "Add Provider" Form
                    yield Label("Add New Provider", classes="section-header-label")
                    with Horizontal(classes="detail-row"):
                        yield Label("Name:", classes="detail-label")
                        yield Input(placeholder="e.g., openai_new", id="new-provider-name-input", classes="detail-input")
                    with Horizontal(classes="detail-row"):
                        yield Label("Base URL:", classes="detail-label")
                        yield Input(placeholder="API URL", id="new-provider-baseurl-input", classes="detail-input")
                    with Horizontal(classes="detail-row"):
                        yield Label("Env Key:", classes="detail-label")
                        yield Input(placeholder="e.g., OPENAI_API_KEY_NEW", id="new-provider-envkey-input", classes="detail-input")
                    yield Button("Save Provider", id="btn-add-new-provider-action", classes="save-new-button")

                # Create all existing providers
                providers = self.core_app.provider_list()
                for provider in providers:
                    self.provider_widgets[provider.name] = ProviderWidget(provider.name, provider.base_url, provider.env_key)
                    yield self.provider_widgets[provider.name]

            with Horizontal(id="footer"):
                yield Button("Close", id="close-providers-btn", variant="default")

    async def on_mount(self) -> None:
        """Load existing providers and populate the view."""
        self.style_input(self.query_one("#new-provider-name-input", Input))
        self.style_input(self.query_one("#new-provider-envkey-input", Input))
        self.style_input(self.query_one("#new-provider-baseurl-input", Input))

    def style_input(self, input_widget: Input) -> None:
        input_widget.styles.border = "none"
        input_widget.styles.height = 1

    async def handle_providers_updated(self) -> None:
        # get current list of providers from core app
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
            for provider_name in self.provider_widgets.keys():
                if provider_name not in provider_names:
                    # mark for removal
                    removed_name = provider_name
                    break

            # Remove widget
            if removed_name and removed_name in self.provider_widgets: # Ensure widget exists before removal
                await self.provider_widgets[removed_name].remove()
                self.provider_widgets.pop(removed_name)
        else:
            # Provider details might have been edited (number of providers is the same)
            app_providers_list = self.core_app.provider_list()
            for app_provider in app_providers_list:
                if app_provider.name in self.provider_widgets:
                    widget = self.provider_widgets[app_provider.name]
                    # Check if details have changed
                    if widget.base_url != app_provider.base_url or \
                       widget.env_key != app_provider.env_key:
                        await widget.update_provider_details(app_provider.name, app_provider.base_url, app_provider.env_key)


    @on(Button.Pressed, "#btn-add-new-provider-action")
    def handle_save_pressed(self):
        # Send command to core app to add a new provider
        name_input = self.query_one("#new-provider-name-input", Input)
        env_key_input = self.query_one("#new-provider-envkey-input", Input)
        base_url_input = self.query_one("#new-provider-baseurl-input", Input)

        name = name_input.value
        env_key_name = env_key_input.value
        base_url = base_url_input.value
        self.post_message(CommandRequest(f"/provider add {name} {env_key_name} {base_url}"))

        # Clear form
        name_input.value = ""
        env_key_input.value = ""
        base_url_input.value = ""

    @on(Button.Pressed, "#close-providers-btn")
    def handle_close_button_press(self) -> None:
        self.dismiss(False)
