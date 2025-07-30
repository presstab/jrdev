from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label
from textual.containers import Vertical
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.utils.string_utils import is_valid_env_key, is_valid_url


class EditProviderModal(ModalScreen):
    """A modal screen to edit a provider."""

    def __init__(self, provider_name: str) -> None:
        super().__init__()
        self.provider_name = provider_name

    def compose(self):
        with Vertical(id="edit-provider-container"):
            yield Label(f"Edit Provider: {self.provider_name}")
            yield Input(placeholder="Base URL", id="base-url")
            yield Input(placeholder="API Key Environment Variable", id="env-key")
            yield Button("Save", id="save")
            yield Button("Cancel", id="cancel")

    def on_mount(self):
        """Populate the inputs with the existing data."""
        provider = self.app.core_app.get_provider(self.provider_name)
        if provider:
            self.query_one("#base-url", Input).value = provider.base_url
            self.query_one("#env-key", Input).value = provider.env_key

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            base_url = self.query_one("#base-url", Input).value
            env_key = self.query_one("#env-key", Input).value
            if not is_valid_url(base_url):
                self.app.notify("Invalid base URL", severity="error")
                return
            if not is_valid_env_key(env_key):
                self.app.notify("Invalid environment key", severity="error")
                return
            self.post_message(CommandRequest(f"/provider edit {self.provider_name} {env_key} {base_url}"))
            self.app.pop_screen()
        else:
            self.app.pop_screen()
