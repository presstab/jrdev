from textual import on
from textual.color import Color
from textual.app import ComposeResult
from textual.widgets import Button, Label, Switch
from textual.containers import Horizontal, Vertical
from typing import Optional
import logging

from jrdev.ui.textual.terminal_output_widget import TerminalOutputWidget
from jrdev.ui.textual.command_request import CommandRequest
from jrdev.ui.textual_events import TextualEvents
from jrdev.ui.textual.chat_input_widget import ChatInputWidget
from jrdev.messages.thread import MessageThread, USER_INPUT_PREFIX

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

    def __init__(self, core_app, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.core_app = core_app
        self.layout_output = Vertical(id="chat_output_layout")
        self.terminal_button = Button(label="<-- Terminal", id="terminal_button")
        self.context_switch = Switch(value=False, id="context_switch", tooltip="When enabled, summarized information about the project is added as context to the chat, this includes select file summaries, file tree, and a project overview")
        self.context_label = Label("Project Ctx", id="context_label")
        self.input_widget = ChatInputWidget(id="chat_input")
        self.send_commands = True
        self.current_thread_id = "main"

    def compose(self) -> ComposeResult:
        """Compose the widget with terminal output and buttons."""
        with self.layout_output:
            yield self.terminal_output
            with Horizontal(id="buttons"):
                yield self.terminal_button
                yield self.copy_button
                yield self.context_switch
                yield self.context_label
        yield self.input_widget

    async def on_mount(self) -> None:
        """Set up the widget when mounted."""
        await super().on_mount()
        self.terminal_button.can_focus = False
        self.context_switch.can_focus = False
        self.copy_button.styles.dock = "none"
        self.copy_button.styles.margin = (0, 0, 0, 1) # add small space between buttons

        self.layout_output.styles.border = ("round", Color.parse("#63f554"))
        self.layout_output.border_title = "Chat"

        self.input_widget.styles.height = 8  # Fixed rows

        # now load only the active thread’s history:
        self._load_current_thread()

    def _load_current_thread(self) -> None:
        """Clear the output and re–print only messages from the active thread."""
        thread: MessageThread = self.core_app.get_current_thread()
        if not thread:
            return

        if self.current_thread_id == thread.thread_id:
            # already on correct thread
            return

        self.current_thread_id = thread.thread_id

        # clear existing text
        self.terminal_output.text = ""

        # replay the thread’s messages
        for msg in thread.messages:
            role = msg["role"]
            body = msg["content"]
            prefix = "You: "
            text = ""
            if role == "user":
                #strip out context files from content
                before, sep, text = body.partition(USER_INPUT_PREFIX)
            else:
                prefix = "Assistant: "
                text = body
            self.append_text(f"{prefix}{text}\n")

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

    def on_thread_switched(self):
        """Whenever the core tells us the thread changed, re-render."""
        self._load_current_thread()

    def handle_stream_chunk(self, event: TextualEvents.StreamChunk) -> None:
        """
        Only append chunks that belong to the active thread,
        so we don’t mix simultaneous conversations.
        """
        active = self.core_app.get_current_thread()
        if active and event.thread_id == active.thread_id:
            self.append_text(event.chunk)

    def handle_external_update(self, is_enabled: bool) -> None:
        if self.context_switch.value != is_enabled:
            self.set_project_context_on(is_enabled)
