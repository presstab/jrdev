from textual import on
from textual.app import ComposeResult
from textual.widgets import Button, Label, Switch
from textual.containers import Horizontal, Vertical
from typing import Optional
import logging

from jrdev.ui.textual.terminal_output_widget import TerminalOutputWidget
from jrdev.ui.textual.command_request import CommandRequest
from jrdev.ui.textual_events import TextualEvents

logger = logging.getLogger("jrdev")

class ChatViewWidget(TerminalOutputWidget):
    """A widget for displaying chat content with additional controls."""
    
    DEFAULT_CSS = """
    ChatViewWidget {
        layout: vertical;
    }
    #terminal_button {
        height: 1;
        width: auto;
    }
    #context_switch {
        height: 1;
        width: auto;
        margin-left: 1;
        border:  none;
    }
    #buttons {
        height: auto;
        width: 100%;
        layout: horizontal;
    }
    #context_label {
        color: #63f554;
    }
    #context_label:disabled {
        color: #365b2d; 
    }
    """

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.terminal_button = Button(label="<-- Terminal", id="terminal_button")
        self.context_switch = Switch(value=False, id="context_switch", tooltip="When enabled, summarized information about the project is added as context to the chat, this includes select file summaries, file tree, and a project overview")
        self.context_label = Label("Project Ctx", id="context_label")
        self.button_container = Horizontal(id="button_container")
        self.send_commands = True

    def compose(self) -> ComposeResult:
        """Compose the widget with terminal output and buttons."""
        with Vertical():
            yield self.terminal_output
            with Horizontal(id="buttons"):
                yield self.terminal_button
                yield self.copy_button
                yield self.context_switch
                yield self.context_label

    async def on_mount(self) -> None:
        """Set up the widget when mounted."""
        await super().on_mount()
        self.terminal_button.can_focus = False
        self.context_switch.can_focus = False
        self.copy_button.styles.dock = "none"
        self.copy_button.styles.margin = (0, 0, 0, 1) # add small space between buttons

    def set_project_context_on(self, is_on):
        """Is project context enabled or disabled"""
        if self.context_switch.value != is_on:
            self.send_commands = False
            self.context_switch.action_toggle_switch()

    @on(Switch.Changed, "#context_switch")
    def handle_switch_change(self, event: Switch.Changed):
        self.context_label.disabled = event.value == False
        if self.send_commands:
            self.post_message(CommandRequest(f"/projectcontext {'on' if event.value else 'off'}"))
        else:
            self.send_commands = True

    def handle_external_update(self, is_enabled: bool) -> None:
        if self.context_switch.value != is_enabled:
            self.set_project_context_on(is_enabled)