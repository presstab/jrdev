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
import pyperclip

from jrdev.ui.tui.yes_no_modal_screen import YesNoScreen
from jrdev.file_operations.file_utils import get_env_path

logger = logging.getLogger("jrdev")

# Helper function to remove a key from .env file (if present)
def remove_key_from_env_file(env_key, env_path=None):
    env_path = env_path or get_env_path()
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
    ApiKeyEntry {
        align: center middle; /* Center the modal */
    }

    #api-key-container {
        width: 80%; /* Adjusted width */
        height: auto; /* Auto height based on content */
        max-height: 90%; /* Limit max height */
        background: $surface;
        border: round $accent;
        padding: 0; /* No padding on container, handled by header/content/footer */
        layout: vertical;
    }

    #header {
        dock: top;
        height: 3;
        padding: 0 1;
        border-bottom: solid $accent;
        content-align: center middle; /* Center content horizontally and vertically */
    }

    #title {
        width: 100%; /* Ensure title takes full width for centering */
        text-align: center;
        text-style: bold;
        color: $accent;
    }

    #content-area {
        /* height: 1fr; /* Take remaining vertical space - removed for auto height */
        padding: 1;
        overflow-y: auto; /* Add scrollbar if needed */
        height: auto;
    }

    /* Grid for inputs */
    #input-grid {
        grid-size: 5; /* Label, Input, Mask, Paste, Delete/Placeholder */
        grid-gutter: 1 2; /* Row gutter, Column gutter */
        grid-columns: auto 1fr 3 3 3;
        margin-top: 1;
        height: auto; /* Grid height based on content */
    }

    /* Style for Paste Buttons within the grid */
    #paste-button {
        height: 1;
        min-width: 3;
        max-width: 3;
        width: 3;
        border: none;
        margin: 0;
        padding: 0;
        align-vertical: middle;
        text-align: center;
    }

    /* Style for Mask Toggle Buttons within the grid */
    #mask-toggle-button {
        height: 1;
        min-width: 3;
        max-width: 3;
        width: 3;
        border: none;
        margin: 0;
        padding: 0;
        align-vertical: middle;
        text-align: center;
    }

    /* Style for Labels within the grid */
    #input-grid > Label {
        margin: 0;
        padding: 0;
        text-align: right;
        height: 1; /* Match input height */
        align-vertical: middle;
    }

    /* Style for Inputs within the grid */
    #input-grid > Input {
        margin: 0;
        padding: 0;
        height: 1;
        border: none; /* Remove default input border */
    }

    /* Style for Delete Buttons within the grid */
    #input-grid > .delete-button {
        height: 1;
        min-width: 3;
        max-width: 3;
        width: 3;
        border: none;
        margin: 0;
        padding: 0;
        align-vertical: middle;
    }

    #footer {
        dock: bottom;
        height: 3;
        padding: 0 1;
        border-top: solid $accent;
        align: left middle;
    }

    #footer Button {
        margin-left: 1;
        border: none;
    }
    """

    def __init__(self, core_app, providers, mode="first_run", existing_keys=None):
        """
        :param providers: List of provider dicts (with 'name', 'env_key', 'required')
        :param mode: 'first_run' or 'editor'
        :param existing_keys: Optional dict of {env_key: value} for editor mode
        """
        super().__init__()
        self.core_app = core_app
        self.providers = providers
        self.mode = mode
        self.existing_keys = existing_keys or self._load_existing_keys()
        self._masked_keys = {}
        self.delete_buttons = []
        self.input_widgets = {}  # Map env_key to Input widget
        self.button_to_env_key = {}  # Map Button ID to env_key
        self.paste_button_to_env_key = {}  # Map Paste Button ID to env_key
        self.mask_button_to_env_key = {}  # Map Mask Button ID to env_key
        self._pending_delete_env_key = None  # Track which key is pending delete confirmation
        self._pending_delete_provider_name = None
        self._input_mask_state = {}  # Map env_key to bool (True=masked, False=unmasked)

    def _load_existing_keys(self):
        """
        Loads existing API keys from environment variables for editor mode.
        """
        keys = {}
        for provider in self.providers:
            env_key = provider.env_key
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
        with Vertical(id="api-key-container"):
            with Horizontal(id="header"):
                if self.mode == "first_run":
                    yield Label("Enter API Keys", id="title")
                else:
                    yield Label("Edit API Keys", id="title")

            with Vertical(id="content-area"):
                with Grid(id="input-grid"):
                    for provider in self.providers:
                        env_key = provider.env_key

                        # Provider Label
                        yield Label(f"{provider.name.title()} Key:")

                        # Input Field
                        existing_value = self.existing_keys.get(env_key, "") if self.mode == "editor" else ""
                        masked = self._mask_key(existing_value) if self.mode == "editor" and existing_value else ""
                        input_widget = Input(id=f"{provider.name}_key", password=True, placeholder="Show/Hide Key")
                        if masked:
                            input_widget.value = masked
                            self._masked_keys[env_key] = masked
                        self.input_widgets[env_key] = input_widget
                        self._input_mask_state[env_key] = True  # Start masked
                        yield input_widget

                        # Mask Toggle Button
                        mask_button = Button("*", id=f"mask_{env_key}", classes="mask-toggle-button", tooltip="Show/Hide Key")
                        self.mask_button_to_env_key[mask_button.id] = env_key
                        yield mask_button

                        # Paste Button
                        paste_button = Button("\u270e", id=f"paste_{env_key}", classes="paste-button", tooltip="Paste")
                        self.paste_button_to_env_key[paste_button.id] = env_key
                        yield paste_button

                        # Delete Button (Editor Mode Only)
                        if self.mode == "editor":
                            button_delete = Button("X", id=f"delete_{env_key}", classes="delete-button", tooltip="Delete")
                            self.delete_buttons.append(button_delete)
                            self.button_to_env_key[button_delete.id] = env_key
                            yield button_delete
                        else:
                            # Add a placeholder Static if not in editor mode to keep grid alignment
                            yield Static() # Placeholder

            with Horizontal(id="footer"):
                yield Button("Save", id="save", variant="success", tooltip="Save Changes")
                yield Button("Exit", id="exit", variant="error", tooltip="Exit Application" if self.mode == "first_run" else "Close")

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            ret = {}
            for provider in self.providers:
                env_key = provider.env_key
                # Use the stored input widget reference
                input_widget = self.input_widgets.get(env_key)
                if not input_widget:
                    logger.warning(f"Could not find input widget for {env_key}")
                    continue # Should not happen

                value = input_widget.value.strip()
                # In editor mode, if the value is still masked, keep the old value
                if self.mode == "editor":
                    masked = self._masked_keys.get(env_key, None)
                    if masked and value == masked:
                        # User did not change the field, keep the original value
                        value = self.existing_keys.get(env_key, "")
                if provider.required and not value:
                    self.notify(f"Must Enter An Api Key For {provider.name.title()}", severity="warning")
                    return
                if value:
                    ret[env_key] = value
            self.dismiss(ret)
        elif event.button.id == "exit":
            if self.mode == "first_run":
                self.app.exit()
            else:
                self.app.pop_screen()
        elif event.button.id and event.button.id.startswith("delete_"):
            # Handle delete button for a specific provider, but ask for confirmation first
            env_key = self.button_to_env_key.get(event.button.id)
            if not env_key:
                self.notify(f"Could not map button {event.button.id} to env_key", severity="error")
                return

            provider_name = None
            for provider in self.providers:
                if provider.env_key == env_key:
                    provider_name = provider.name
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
                        self.core_app.state.clients.set_client_null(provider_name)
                        self.notify(f"Deleted API key for {provider_name.title()}", severity="info") # Use title case for provider name
                    # Reset pending delete
                    self._pending_delete_env_key = None
                    self._pending_delete_provider_name = None

            self._pending_delete_env_key = env_key
            self._pending_delete_provider_name = provider_name
            prompt = f"Are you sure you want to delete API key for {provider_name.title()}?" # Use title case
            self.app.push_screen(YesNoScreen(prompt), handle_key_delete)
        elif event.button.id and event.button.id.startswith("paste_"):
            # Handle paste button: paste clipboard contents into the corresponding input
            env_key = self.paste_button_to_env_key.get(event.button.id)
            if not env_key:
                self.notify(f"Could not map paste button {event.button.id} to env_key", severity="error")
                return
            input_widget: Input = self.input_widgets.get(env_key)
            if not input_widget:
                self.notify(f"Could not find input widget for {env_key}", severity="error")
                return
            # Use pyperclip to get clipboard contents
            try:
                clipboard_text = pyperclip.paste()
            except Exception as e:
                self.notify(f"Could not access clipboard: {e}", severity="error")
                return
            if clipboard_text is not None and clipboard_text != "":
                input_widget.value = clipboard_text
                # If the field was masked, unmask it so user can see what was pasted
                self._input_mask_state[env_key] = False
                input_widget.password = False
            else:
                self.notify("Clipboard is empty or unavailable.", severity="warning")
        elif event.button.id and event.button.id.startswith("mask_"):
            # Handle mask toggle button: toggle password masking for the corresponding input
            env_key = self.mask_button_to_env_key.get(event.button.id)
            if not env_key:
                self.notify(f"Could not map mask button {event.button.id} to env_key", severity="error")
                return
            input_widget: Input = self.input_widgets.get(env_key)
            if not input_widget:
                self.notify(f"Could not find input widget for {env_key}", severity="error")
                return
            # Toggle mask state
            current_masked = self._input_mask_state.get(env_key, True)
            if current_masked:
                # Unmask: show real value if available
                if self.mode == "editor":
                    # If the value is currently masked, replace with real value
                    masked = self._masked_keys.get(env_key, None)
                    if masked and input_widget.value == masked:
                        real_value = self.existing_keys.get(env_key, "")
                        input_widget.value = real_value
                input_widget.password = False
                self._input_mask_state[env_key] = False
            else:
                # Mask: show masked value if available
                if self.mode == "editor":
                    real_value = input_widget.value
                    masked = self._mask_key(real_value)
                    input_widget.value = masked
                    self._masked_keys[env_key] = masked
                input_widget.password = True
                self._input_mask_state[env_key] = True
