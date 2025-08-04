from textual.widgets import Input
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.settings.model_management.base_model_modal import BaseModelModal
from jrdev.ui.tui.settings.model_management.remove_model_modal import RemoveResourceModal
from jrdev.utils.string_utils import is_valid_env_key, is_valid_url


class EditProviderModal(BaseModelModal):
    """A modal screen to edit a provider."""

    def __init__(self, provider_name: str) -> None:
        super().__init__()
        self.provider_name = provider_name

    def compose(self):
        container, header = self.build_container("edit-provider-container", f"Edit {self.provider_name}")
        with container:
            yield header
            yield self.labeled_row("Base URL:", Input(placeholder="Base URL", id="base-url"))
            yield self.labeled_row("API Key Environment Variable:", Input(placeholder="API Key Environment Variable", id="env-key"))
            yield self.actions_row()

    def on_mount(self):
        """Populate the inputs with the existing data."""
        all_providers = self.app.jrdev.provider_list()
        provider = next((p for p in all_providers if p.name == self.provider_name), None)
        if provider:
            self.query_one("#base-url", Input).value = provider.base_url
            self.query_one("#env-key", Input).value = provider.env_key

    def on_button_pressed(self, event):
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
        elif event.button.id == "remove":
            self.app.push_screen(RemoveResourceModal(self.provider_name, resource_type="provider"))
        else:
            self.app.pop_screen()
