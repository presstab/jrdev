from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label
from textual.containers import Vertical
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.utils.string_utils import is_valid_name, is_valid_env_key, is_valid_url


class AddProviderModal(ModalScreen):
    """A modal screen to add a new provider."""

    DEFAULT_CSS = """
    AddProviderModal {
        align: center middle;
    }

    #add-provider-container {
        width: 50;
        height: auto;
        padding: 1 2;
        border: round #2a2a2a;
        background: #1e1e1e;
        gap: 1;
    }
    """

    def compose(self):
        with Vertical(id="add-provider-container"):
            yield Label("Add New Provider")
            yield Input(placeholder="Provider Name", id="provider-name")
            yield Input(placeholder="Base URL", id="base-url")
            yield Input(placeholder="API Key Environment Variable", id="env-key")
            yield Button("Save", id="save")
            yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            name = self.query_one("#provider-name", Input).value
            base_url = self.query_one("#base-url", Input).value
            env_key = self.query_one("#env-key", Input).value
            if not is_valid_name(name):
                self.app.notify("Invalid provider name", severity="error")
                return
            if not is_valid_url(base_url):
                self.app.notify("Invalid base URL", severity="error")
                return
            if not is_valid_env_key(env_key):
                self.app.notify("Invalid environment key", severity="error")
                return
            self.post_message(CommandRequest(f"/provider add {name} {env_key} {base_url}"))
            self.app.pop_screen()
        else:
            self.app.pop_screen()
