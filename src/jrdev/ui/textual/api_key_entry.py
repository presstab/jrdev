from textual import events
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Input, Static
from textual.css.query import NoMatches
import logging
import json
import os
from pathlib import Path

from .yes_no_modal_screen import YesNoScreen

logger = logging.getLogger("jrdev")

# Helper function to remove a key from .env file (if present)
def remove_key_from_env_file(env_key, env_path=None):
    env_path = env_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if not line.strip().startswith(f"{env_key}="):
                new_lines.append(line)
        with open(env_path, "w") as f:
            f.writelines(new_lines)
    except Exception as e:
        logger.error(f"Error removing {env_key} from .env: {e}")

class ApiKeyEntry(Screen[dict]):
    """
    Modal Dialog To Enter or Edit API Keys.
    Supports two modes:
      - 'first_run': For initial setup, requires all required keys.
      - 'editor': For editing existing keys, loads and masks current values.
    """
    CSS = """
    Vertical {
        margin: 0;
        padding: 0 4;
        height: auto;
    }

    Horizontal {
        margin: 0 0 1 0;
        padding: 0;
        height: auto;
    }

    Label {
        margin: 0;
        padding: 0;
        width: 16;
    }

    Input {
        margin: 0;
        padding: 0;
        height: 1;
        border: none;
    }
    
    #title {
        text-align: center;
        margin-bottom: 1;
    }
    #mode-label {
        text-align: center;
        color: $secondary;
        margin-bottom: 1;
    }
    """

    def __init__(self, providers, mode="first_run", existing_keys=None):
        """
        :param providers: List of provider dicts (with 'name', 'env_key', 'required')
        :param mode: 'first_run' or 'editor'
        :param existing_keys: Optional dict of {env_key: value} for editor mode
        """
        super().__init__()
        self.providers = providers
        self.mode = mode
        self.existing_keys = existing_keys or self._load_existing_keys()
        self._masked_keys = {}
        self.delete_buttons = []
        self.input_widgets = {}  # Map env_key to Input widget
        self.button_to_env_key = {}  # Map Button to env_key
        self._pending_delete_env_key = None  # Track which key is pending delete confirmation
        self._pending_delete_provider_name = None

    def _load_existing_keys(self):
        """
        Loads existing API keys from environment variables for editor mode.
        """
        keys = {}
        for provider in self.providers:
            env_key = provider["env_key"]
            value = os.environ.get(env_key, "")
            if value:
                keys[env_key] = value
        return keys

    def _mask_key(self, value):
        if not value:
            return ""
        # Show only last 4 chars, mask the rest
        if len(value) <= 4:
            return "*" * len(value)
        return "*" * (len(value) - 4) + value[-4:]

    def compose(self) -> ComposeResult:
        with Vertical():
            if self.mode == "first_run":
                yield Label("Enter API Keys", id="title")
                yield Label("First-time setup: Please enter all required API keys.", id="mode-label")
            else:
                yield Label("Edit API Keys", id="title")
                yield Label("Editor mode: Existing keys are masked. Edit and save as needed.", id="mode-label")
            for provider in self.providers:
                with Horizontal():
                    yield Label(f"{provider['name'].title()} Key:")
                    # In editor mode, prefill with masked value if exists
                    env_key = provider["env_key"]
                    existing_value = self.existing_keys.get(env_key, "") if self.mode == "editor" else ""
                    masked = self._mask_key(existing_value) if self.mode == "editor" and existing_value else ""
                    input_widget = Input(id=f"{provider['name']}_key", password=True)
                    input_widget.styles.width = "60%"
                    input_widget.styles.min_width = 5
                    if masked:
                        input_widget.value = masked
                        self._masked_keys[env_key] = masked
                    self.input_widgets[env_key] = input_widget
                    yield input_widget
                    if self.mode == "editor":
                        button_delete = Button("X", id=f"delete_{env_key}")
                        button_delete.styles.height = 1
                        button_delete.styles.max_width = 3
                        button_delete.styles.min_width = 3
                        self.delete_buttons.append(button_delete)
                        self.button_to_env_key[button_delete.id] = env_key
                        yield button_delete
            with Horizontal():
                yield Button("Save", id="save")
                yield Button("Exit", id="exit")
            spacer = Static()
            spacer.styles.height = "1fr"
            yield spacer

    def _on_mount(self, event: events.Mount) -> None:
        super()._on_mount(event)
        for button in self.delete_buttons:
            button.styles.border = "none"
            button.styles.height = 1

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            ret = {}
            for provider in self.providers:
                env_key = provider["env_key"]
                input_widget = self.query_one(f"#{provider['name']}_key", Input)
                value = input_widget.value.strip()
                # In editor mode, if the value is still masked, keep the old value
                if self.mode == "editor":
                    masked = self._masked_keys.get(env_key, None)
                    if masked and value == masked:
                        # User did not change the field, keep the original value
                        value = self.existing_keys.get(env_key, "")
                if provider["required"] and not value:
                    self.notify(f"Must Enter An Api Key For {provider['name'].title()}", severity="warning")
                    return
                if value:
                    ret[env_key] = value
            self.dismiss(ret)
        elif event.button.id == "exit":
            self.app.pop_screen()
        elif event.button.id and event.button.id.startswith("delete_"):
            # Handle delete button for a specific provider, but ask for confirmation first
            env_key = event.button.id[len("delete_"):]
            provider_name = None
            for provider in self.providers:
                if provider["env_key"] == env_key:
                    provider_name = provider["name"]
                    break
            if provider_name is None:
                self.notify(f"Unknown provider for env_key {env_key}", severity="error")
                return

            def handle_key_delete(confirmed: bool):
                # Check if we have a pending delete and if so, process the result
                if self._pending_delete_env_key is not None:
                    if confirmed:
                        env_key = self._pending_delete_env_key
                        provider_name = self._pending_delete_provider_name
                        # Remove from environment (if present)
                        if env_key in os.environ:
                            del os.environ[env_key]
                        # Remove from .env file (if present)
                        remove_key_from_env_file(env_key)
                        # Remove from existing_keys and masked_keys
                        if env_key in self.existing_keys:
                            del self.existing_keys[env_key]
                        if env_key in self._masked_keys:
                            del self._masked_keys[env_key]
                        # Clear the input field
                        input_widget = self.input_widgets.get(env_key)
                        if input_widget:
                            input_widget.value = ""
                        self.notify(f"Deleted API key for {env_key}", severity="info")
                    # Reset pending delete
                    self._pending_delete_env_key = None
                    self._pending_delete_provider_name = None

            self._pending_delete_env_key = env_key
            self._pending_delete_provider_name = provider_name
            prompt = f"Are you sure you want to delete API key for {provider_name}?"
            self.app.push_screen(YesNoScreen(prompt), handle_key_delete)
