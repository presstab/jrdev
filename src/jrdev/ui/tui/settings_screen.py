import logging
from typing import Any, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Static

from jrdev.ui.tui.providers_widget import ProvidersWidget
from jrdev.ui.tui.models_widget import ModelsWidget
from jrdev.ui.tui.api_key_entry import ApiKeyEntry
from jrdev.ui.tui.terminal_styles_widget import TerminalStylesWidget

logger = logging.getLogger("jrdev")

class SettingsScreen(ModalScreen):
    """Modal screen for managing Providers and Models with sidebar navigation."""

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: round $accent;
        padding: 0;
        layout: vertical;
    }

    #header {
        dock: top;
        height: 5;
        padding: 0 0;
        border-bottom: solid $accent;
        layout: vertical;
    }

    #header-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        height: 2;
    }

    #header-subtitle {
        width: 100%;
        content-align: center top;
        color: $text-muted;
        height: 2;
        margin-top: 0;
        margin-bottom: 0;
        text-style: italic;
    }

    #main-content-horizontal {
        height: 1fr;
        layout: horizontal;
    }

    #sidebar {
        width: 20%;
        height: 100%;
        border-right: solid $panel;
        padding: 1 0;
    }

    #sidebar-title {
        height: 3;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
        color: $text;
        border-bottom: solid $panel;
    }

    .sidebar-button {
        width: 100%;
        height: 3;
        margin: 1 0 0 0;
        border: none;
    }
    .sidebar-button:hover {
        background: $primary-darken-1;
    }
    .sidebar-button.selected {
        background: $primary;
        text-style: bold;
    }

    #content-area {
        width: 80%;
        height: 100%;
        layout: vertical;
    }

    #providers-view, #models-view, #styles-view {
        height: 1fr;
        display: block;
        padding: 0;
        overflow-y: auto;
        overflow-x: hidden;
    }

    #footer {
        dock: bottom;
        height: 3;
        padding: 0 1;
        border-top: solid $accent;
        align: left middle;
    }
    #footer Button {
        margin-right: 1;
        border: none;
    }
    """

    def __init__(self, core_app: Any) -> None:
        super().__init__()
        self.core_app = core_app
        self.active_view = "providers"  # 'providers', 'models', or 'styles'
        self.providers_widget = ProvidersWidget(core_app=self.core_app)
        self.models_widget = ModelsWidget(core_app=self.core_app)
        self.styles_widget = TerminalStylesWidget(core_app=self.core_app)
        self.header_subtitle_label = None

    def get_active_subtitle(self) -> str:
        if self.active_view == "providers":
            return "Api Providers"
        elif self.active_view == "models":
            return "Edit Models"
        elif self.active_view == "styles":
            return "Terminal Styles"
        else:
            return ""

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-container"):
            # Header
            with Vertical(id="header"):
                yield Label("Settings", id="header-title")
                self.header_subtitle_label = Label(self.get_active_subtitle(), id="header-subtitle")
                yield self.header_subtitle_label
            # Main content area (Sidebar + Content)
            with Horizontal(id="main-content-horizontal"):
                # Sidebar
                with Vertical(id="sidebar"):
                    yield Button("API Keys", id="btn-api-keys", classes="sidebar-button")
                    yield Button("Providers", id="btn-providers", classes="sidebar-button selected")
                    yield Button("Models", id="btn-models", classes="sidebar-button")
                    yield Button("Terminal Styles", id="btn-styles", classes="sidebar-button")
                # Content Area
                with Vertical(id="content-area"):
                    with ScrollableContainer(id="providers-view"):
                        yield self.providers_widget
                    with ScrollableContainer(id="models-view"):
                        yield self.models_widget
                    with ScrollableContainer(id="styles-view"):
                        yield self.styles_widget
            # Footer
            with Horizontal(id="footer"):
                yield Button("Close", id="close-settings-btn", variant="default")

    def on_mount(self) -> None:
        self.update_view_visibility()
        # Focus the first sidebar button
        self.query_one("#btn-providers", Button).focus()
        # Set the correct subtitle
        if self.header_subtitle_label:
            self.header_subtitle_label.update(self.get_active_subtitle())

    def update_view_visibility(self) -> None:
        views = {
            "providers": "#providers-view",
            "models": "#models-view",
            "styles": "#styles-view",
        }
        buttons = {
            "providers": "#btn-providers",
            "models": "#btn-models",
            "styles": "#btn-styles",
        }
        for view_name, view_id in views.items():
            try:
                view_widget = self.query_one(view_id)
                view_widget.styles.display = "block" if view_name == self.active_view else "none"
            except Exception as e:
                logger.error(f"Error finding view {view_id}: {e}")
        # Update the subtitle label
        if self.header_subtitle_label:
            self.header_subtitle_label.update(self.get_active_subtitle())

    @on(Button.Pressed, ".sidebar-button")
    def handle_sidebar_button(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-providers":
            self.active_view = "providers"
            self.query_one("#btn-providers", Button).focus()
            self.update_view_visibility()
        elif button_id == "btn-models":
            self.active_view = "models"
            self.query_one("#btn-models", Button).focus()
            self.update_view_visibility()
        elif button_id == "btn-styles":
            self.active_view = "styles"
            self.query_one("#btn-styles", Button).focus()
            self.update_view_visibility()
        elif button_id == "btn-api-keys":
            self.open_api_keys_modal()

    @on(Button.Pressed, "#close-settings-btn")
    def handle_close(self) -> None:
        self.dismiss(None)

    def open_api_keys_modal(self) -> None:
        def save_keys(keys: dict):
            self.core_app.save_keys(keys)
            self.run_worker(self.core_app.reload_api_clients())
        providers = self.core_app.provider_list()
        self.app.push_screen(ApiKeyEntry(core_app=self.core_app, providers=providers, mode="editor"), save_keys)
