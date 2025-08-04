from textual.widgets import Input
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.settings.model_management.base_model_modal import BaseModelModal
from jrdev.utils.string_utils import is_valid_name, is_valid_env_key, is_valid_url


class AddProviderModal(BaseModelModal):
    """A modal screen to add a new provider."""

    def compose(self):
        container, header = self.build_container("add-provider-container", "Add New Provider")
        with container:
            yield header
            yield self.labeled_row("Provider Name:", Input(placeholder="Provider Name", id="provider-name"))
            yield self.labeled_row("Base URL:", Input(placeholder="Base URL", id="base-url"))
            yield self.labeled_row("API Key Environment Variable:", Input(placeholder="API Key Environment Variable", id="env-key"))
            yield self.actions_row()

    def on_button_pressed(self, event):
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
