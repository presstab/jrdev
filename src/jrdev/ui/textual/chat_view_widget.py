import os
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Label, Switch
from textual.color import Color
from textual.scroll_view import ScrollView
from typing import Optional
import logging

from jrdev.ui.textual.command_request import CommandRequest
from jrdev.ui.textual_events import TextualEvents
from jrdev.ui.textual.chat_input_widget import ChatInputWidget
from jrdev.messages.thread import MessageThread, USER_INPUT_PREFIX
from jrdev.ui.textual.message_bubble import MessageBubble

logger = logging.getLogger("jrdev")

MAX_BUBBLES = 50

class ChatViewWidget(Widget):
    """A widget for displaying chat content with message bubbles and controls."""

    DEFAULT_CSS = """
    ChatViewWidget {
        layout: vertical;
        height: 100%;
        min-height: 0;
    }
    #chat_output_layout {
        layout: vertical;
        height: 1fr;
        min-height: 0;
    }
    #chat_controls_container {
        height: auto;
        width: 100%;
        layout: horizontal;
        border-top: #63f554;
        border-bottom: none;
        border-left: none;
        border-right: none;
    }
    #chat_context_display_container {
        height: auto; /* Allow wrapping for multiple files */
        width: 100%;
        layout: horizontal;
        padding: 0 1; /* Horizontal padding */
    }
    #chat_context_title_label {
        height: 1;
        width: auto;
        margin-right: 1;
        color: #63f554; /* Match other labels */
    }
    #chat_context_files_label {
        height: 1;
        width: 1fr; /* Fill available space */
        color: #9b65ff; /* Match purplish color from filtered directory tree */
        text-style: italic;
    }
    #terminal_button {
        height: 1;
        width: auto;
    }
    #context_switch {
        height: 1;
        width: auto;
        margin-left: 1;
        border: none;
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

        #this is our scrollable area:
        self.message_scroller = VerticalScroll(id="scrolling_layout")

        #controls and input
        self.layout_output = Vertical(id="chat_output_layout")
        self.terminal_button = Button(label="<-- Terminal", id="terminal_button")
        self.context_switch = Switch(value=False, id="context_switch", tooltip="When enabled, summarized information about the project is added as context to the chat, this includes select file summaries, file tree, and a project overview")
        self.context_label = Label("Project Ctx", id="context_label")
        self.input_widget = ChatInputWidget(id="chat_input")

        # Chat context display widgets
        self.chat_context_title_label = Label("Chat Context:", id="chat_context_title_label")
        self.chat_context_files_label = Label("None", id="chat_context_files_label")
        
        self.send_commands = True # For context_switch logic
        self.current_thread_id: Optional[str] = None
        self.MAX_BUBBLES = MAX_BUBBLES

    def compose(self) -> ComposeResult:
        """Compose the widget with controls, message scroll view, and input area."""
        with self.layout_output:
            yield self.message_scroller
            with Horizontal(id="chat_controls_container"):
                yield self.terminal_button
                yield self.context_switch
                yield self.context_label
            with Horizontal(id="chat_context_display_container"):
                yield self.chat_context_title_label
                yield self.chat_context_files_label
        yield self.input_widget

    async def on_mount(self) -> None:
        """Set up the widget when mounted."""
        self.layout_output.styles.border = ("round", Color.parse("#63f554"))
        self.layout_output.border_title = "Chat"

        self.terminal_button.can_focus = False
        self.context_switch.can_focus = False

        self.input_widget.styles.height = 8

        self.message_scroller.styles.height = "1fr"
        self.message_scroller.styles.min_height = 0
        self.message_scroller.show_vertical_scrollbar = True
        self.message_scroller.horizontal_scrollbar

        await self._load_current_thread()

    async def _prune_bubbles(self) -> None:
        """Removes the oldest bubbles if the count exceeds MAX_BUBBLES."""
        bubbles = [child for child in self.message_scroller.children if isinstance(child, MessageBubble)]
        if len(bubbles) > self.MAX_BUBBLES:
            num_to_remove = len(bubbles) - self.MAX_BUBBLES
            for old_bubble in list(bubbles[:num_to_remove]): 
                await old_bubble.remove()

    async def _update_chat_context_display(self) -> None:
        """Updates the label displaying the current chat context files."""
        thread: Optional[MessageThread] = self.core_app.get_current_thread()
        if thread:
            context_paths = thread.get_context_paths()
            if context_paths:
                filenames = [os.path.basename(p) for p in context_paths]
                self.chat_context_files_label.update(", ".join(filenames))
            else:
                self.chat_context_files_label.update("Empty")
        else:
            self.chat_context_files_label.update("Empty")

    async def _load_current_thread(self) -> None:
        """Clear the output and re-render messages from the active thread as bubbles."""
        thread: Optional[MessageThread] = self.core_app.get_current_thread()
        
        if not thread:
            if self.current_thread_id is not None:
                 await self.message_scroller.remove_children()
                 self.current_thread_id = None
            await self._update_chat_context_display() # Update context display for no thread
            return

        # update context file list
        await self._update_chat_context_display()

        if self.current_thread_id == thread.thread_id and self.message_scroller.children:
            # If it's the same thread and we already have bubbles, just scroll
            self.message_scroller.scroll_end(animate=False)
            return

        self.current_thread_id = thread.thread_id
        await self.message_scroller.remove_children()

        for msg in thread.messages:
            role = msg["role"]
            body = msg["content"]
            
            display_content = ""
            if role == "user":
                if USER_INPUT_PREFIX in body:
                    display_content = body.split(USER_INPUT_PREFIX, 1)[1]
                else:
                    display_content = body
            else:
                display_content = body
            
            bubble = MessageBubble(display_content, role=role)
            await self.message_scroller.mount(bubble)

        await self._prune_bubbles()
        await self._update_chat_context_display() # Update context display after loading thread messages
        self.message_scroller.scroll_end(animate=False)

    async def add_user_message(self, raw_user_input: str) -> None:
        """
        Adds a new user message bubble to the UI. 
        Called by JrDevUI when user submits input via ChatInputWidget.
        """
        bubble = MessageBubble(raw_user_input, role="user")
        await self.message_scroller.mount(bubble)
        await self._prune_bubbles()
        # Context display is updated when the thread itself is updated (e.g., via _load_current_thread)
        self.message_scroller.scroll_end(animate=False)

    async def handle_stream_chunk(self, event: TextualEvents.StreamChunk) -> None:
        """Handles incoming stream chunks for assistant replies."""
        active_thread = self.core_app.get_current_thread()
        if not active_thread or event.thread_id != active_thread.thread_id:
            return

        if event.thread_id != self.current_thread_id:
            logger.warning(f"Stream chunk for thread {event.thread_id} but ChatViewWidget is displaying {self.current_thread_id}. Ignoring.")
            return

        bubbles = [child for child in self.message_scroller.children if isinstance(child, MessageBubble)]
        last_bubble = bubbles[-1] if bubbles else None

        if last_bubble and last_bubble.role == "assistant":
            last_bubble.append_chunk(event.chunk)
        else:
            new_bubble = MessageBubble(event.chunk, role="assistant")
            await self.message_scroller.mount(new_bubble)
            await self._prune_bubbles()

        self.message_scroller.scroll_end(animate=False)

    def set_project_context_on(self, is_on: bool) -> None:
        """Programmatically sets the project context switch state."""
        if self.context_switch.value != is_on:
            self.send_commands = False
            self.context_switch.action_toggle_switch()

    @on(Switch.Changed, "#context_switch")
    def handle_switch_change(self, event: Switch.Changed) -> None:
        """Handles user interaction with the context switch."""
        self.context_label.disabled = not event.value
        if self.send_commands:
            self.post_message(CommandRequest(f"/projectcontext {'on' if event.value else 'off'}"))
        else:
            self.send_commands = True # Reset for next user interaction

    async def on_thread_switched(self) -> None:
        """Called when the core application signals a thread switch."""
        await self._load_current_thread()

    def handle_external_update(self, is_enabled: bool) -> None:
        """Handles external updates to the project context state (e.g., from core app)."""
        if self.context_switch.value != is_enabled:
            self.set_project_context_on(is_enabled)
