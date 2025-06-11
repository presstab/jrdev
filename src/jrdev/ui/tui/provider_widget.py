from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, Input

from jrdev.ui.tui.command_request import CommandRequest
from jrdev.utils.string_utils import is_valid_env_key, is_valid_url


class ProviderWidget(Widget):
    DEFAULT_CSS = """
    ProviderWidget {
        margin: 0;
        padding: 0;
        height: auto;
    }
    #widget-container {
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
    """

    def __init__(self, provider_name, base_url, env_key):
        super().__init__()
        self.provider_name = provider_name
        self.base_url = base_url
        self.env_key = env_key
        self.edit_mode = False

        # Buttons for edit mode
        self.btn_edit = Button("Edit", id="btn-edit", variant="success", classes="action-button")
        self.btn_remove = Button("Remove", id="btn-remove", variant="success", classes="action-button")
        self.btn_save = Button("Save Edits", id="btn-save", variant="success", classes="action-button")
        self.btn_cancel = Button("Cancel", id="btn-cancel", variant="success", classes="action-button")
        self.btn_save.display = False
        self.btn_cancel.display = False

        # Buttons for removal confirmation
        self.btn_confirm_remove = Button("Confirm Removal", id="btn-confirm-remove", variant="error", classes="action-button")
        self.btn_cancel_remove = Button("Cancel", id="btn-cancel-remove", variant="error", classes="action-button")
        self.btn_confirm_remove.display = False
        self.btn_cancel_remove.display = False

        # Inputs
        self.input_url = Input(value=f"{self.base_url}", id="input-url", classes="detail-input", disabled=True, tooltip="Base URL of the API provider.")
        self.input_envkey = Input(value=f"{self.env_key}", id="input-envkey", classes="detail-input", disabled=True, tooltip="Name of the environment variable that holds the API key, not the API key itself.")

    def compose(self) -> ComposeResult:
        with Vertical(id="widget-container"):
            yield Label(f"{self.provider_name}", classes="form-header-label")
            with Horizontal(classes="form-row"):
                yield Label("Base URL:", classes="form-label")
                yield self.input_url
            with Horizontal(classes="form-row"):
                yield Label("Env Key: ", classes="form-label")
                yield self.input_envkey
            with Horizontal(classes="form-row"):
                yield self.btn_edit
                yield self.btn_remove
                yield self.btn_confirm_remove
                yield self.btn_cancel_remove
                yield self.btn_save
                yield self.btn_cancel

    async def on_mount(self) -> None:
        """Load manual styling"""
        self.style_input(self.input_url)
        self.style_input(self.input_envkey)

    def style_input(self, input_widget: Input) -> None:
        input_widget.styles.border = "none"
        input_widget.styles.height = 1

    def set_edit_mode(self, is_edit_mode: bool) -> None:
        self.edit_mode = is_edit_mode
        input_url = self.query_one("#input-url", Input)
        input_envkey = self.query_one("#input-envkey", Input)

        # enable or disable the input widgets
        input_url.disabled = not input_url.disabled
        input_envkey.disabled = not input_envkey.disabled

        # toggle button visibility
        self.btn_edit.display = not self.btn_edit.display
        self.btn_remove.display = not self.btn_remove.display
        self.btn_save.display = not self.btn_save.display
        self.btn_cancel.display = not self.btn_cancel.display

    async def update_provider_details(self, new_name: str, new_base_url: str, new_env_key: str) -> None:
        """Update the provider's details and refresh the UI elements."""
        self.provider_name = new_name
        self.base_url = new_base_url
        self.env_key = new_env_key

        # Update UI elements
        header_label = self.query_one(".form-header-label", Label)
        header_label.update(new_name)

        input_url = self.query_one("#input-url", Input)
        input_url.value = new_base_url

        input_envkey = self.query_one("#input-envkey", Input)
        input_envkey.value = new_env_key

    @on(Button.Pressed, "#btn-edit")
    async def handle_edit_clicked(self, event: Button.Pressed) -> None:
        self.set_edit_mode(True)

    @on(Button.Pressed, "#btn-remove")
    async def handle_remove_clicked(self, event: Button.Pressed) -> None:
        # Prompt for removal confirmation
        self.btn_edit.display = False
        self.btn_remove.display = False
        self.btn_confirm_remove.display = True
        self.btn_cancel_remove.display = True

    @on(Button.Pressed, "#btn-confirm-remove")
    async def handle_confirm_remove(self, event: Button.Pressed) -> None:
        # Perform removal
        self.post_message(CommandRequest(f"/provider remove {self.provider_name}"))
        # Restore original buttons
        self.btn_confirm_remove.display = False
        self.btn_cancel_remove.display = False
        self.btn_edit.display = True
        self.btn_remove.display = True

    @on(Button.Pressed, "#btn-cancel-remove")
    async def handle_cancel_remove(self, event: Button.Pressed) -> None:
        # Cancel removal and restore buttons
        self.btn_confirm_remove.display = False
        self.btn_cancel_remove.display = False
        self.btn_edit.display = True
        self.btn_remove.display = True

    @on(Button.Pressed, "#btn-cancel")
    async def handle_cancel_clicked(self, event: Button.Pressed) -> None:
        self.set_edit_mode(False)

    @on(Button.Pressed, "#btn-save")
    async def handle_save_clicked(self, event: Button.Pressed) -> None:
        base_url = self.query_one("#input-url", Input).value
        env_key_name = self.query_one("#input-envkey", Input).value

        # Validate inputs using the same logic as the command handler
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

        self.post_message(CommandRequest(f"/provider edit {self.provider_name} {env_key_name} {base_url}"))
        self.set_edit_mode(False)
