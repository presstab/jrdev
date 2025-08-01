from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label
from textual.containers import Vertical
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.utils.string_utils import is_valid_env_key, is_valid_url


class EditProviderModal(ModalScreen):
    """A small, compact modal screen to edit a provider."""

    DEFAULT_CSS = """
    EditProviderModal {
        align: center middle;
        background: transparent;
    }
    #edit-provider-container {
        width: 28;
        min-width: 24;
        max-width: 32;
        height: auto;
        padding: 0 1;
        margin: 0;
        align: center middle;
        border: round #2a2a2a;
        background: #1e1e1e 80%;
        overflow: hidden;
        content-align: center middle;
    }
    #edit-provider-container > Label {
        padding: 0;
        margin: 0 0 1 0;
    }
    #edit-provider-container > Input,
    #edit-provider-container > Button {
        height: 1;
        margin: 0;
    }
    """

    def __init__(self, provider_name: str) -> None:
        super().__init__()
        self.provider_name = provider_name
        self.input_baseurl = Input(placeholder="Base URL", id="base-url")
        self.input_apikey = Input(placeholder="API Key Env Var", id="env-key")

    def compose(self):
        with Vertical(id="edit-provider-container"):
            yield Label(f"Edit {self.provider_name}")
            yield self.input_baseurl
            yield self.input_apikey
            yield Button("Save", id="save")
            yield Button("Cancel", id="cancel")

    def on_mount(self):
        """Populate the inputs with the existing data."""
        all_providers = self.app.jrdev.provider_list()
        provider = next((p for p in all_providers if p.name == self.provider_name), None)
        if provider:
            self.input_baseurl.value = provider.base_url
            self.input_apikey.value = provider.env_key

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
