from textual import events, on
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button
from textual.message import Message
from typing import Dict, List, Optional
import logging

from jrdev.messages.thread import MessageThread
from jrdev.ui.tui.command_request import CommandRequest

logger = logging.getLogger("jrdev")

class ChatList(Widget):
    class NewChatActivated(Message):
        """Message sent when a new chat is created and activated."""
        def __init__(self, thread_id: str) -> None:
            self.thread_id = thread_id
            super().__init__()

    def __init__(self, core_app, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.core_app = core_app
        self.buttons: Dict[str, Button] = {} # id -> Button
        self.threads: Dict[str, MessageThread] = {} # id -> MsgThread
        self.active_thread_id: Optional[str] = None
        self.new_button = Button(label="+ New Chat", id="new_thread", classes="sidebar_button")

    def compose(self) -> ComposeResult:
        for button in self.buttons.values():
            yield button
        yield self.new_button

    async def on_mount(self) -> None:
        self.can_focus = False
        for button in self.buttons.values():
            self.style_button(button)
        self.style_button(self.new_button)

    def style_button(self, btn):
        btn.can_focus = False
        btn.styles.border = "none"
        btn.styles.min_width = 4
        btn.styles.width = "100%"
        btn.styles.align_horizontal = "center"

    async def add_thread(self, msg_thread: MessageThread) -> None:
        # filter out any router threads
        thread_type = msg_thread.metadata.get("type")
        if thread_type and thread_type == "router":
            return

        tid = msg_thread.thread_id
        name = tid.removeprefix("thread_")
        if msg_thread.name:
            name = msg_thread.name
        btn = Button(label=name, id=tid, classes="sidebar_button")
        self.buttons[tid] = btn
        self.threads[tid] = msg_thread
        await self.mount(btn)
        # if this is the first thread, make it active
        if self.active_thread_id is None:
            self.set_active(tid)
        self.style_button(btn)

    def check_threads(self, all_threads: List[str]) -> None:
        # check our list of threads against the list from app state
        to_remove = [tid for tid in self.threads.keys() if tid not in all_threads]
        for tid in to_remove:
            btn = self.buttons.pop(tid, None)
            if btn is not None:
                btn.remove()
            self.threads.pop(tid, None)
            if self.active_thread_id == tid:
                self.active_thread_id = None

    def set_active(self, thread_id: str) -> None:
        # if this is already active thread, then ignore
        if self.active_thread_id == thread_id:
            return

        # remove “active” from old
        if self.active_thread_id and self.active_thread_id in self.buttons:
            self.buttons[self.active_thread_id].remove_class("active")
        # set new
        self.active_thread_id = thread_id
        if thread_id in self.buttons:
            self.buttons[thread_id].add_class("active")

    @on(Button.Pressed, ".sidebar_button")
    async def handle_thread_button_click(self, event: Button.Pressed):
        btn = event.button

        # check if it is the new thread button
        if btn.id == "new_thread":
            # Post the command to create a new thread
            self.post_message(CommandRequest("/thread new"))
            # Wait for the thread to be created in the backend, then update UI
            # We'll optimistically try to find the new thread after a short delay
            # but the main UI will also update us via ChatThreadUpdate event.
            # Instead, we emit a message to parent to switch to the new chat after it's created.
            # So, we do nothing here except post the command.
            return

        if btn.id not in self.buttons:
            # ignore button if it doesn't belong to chat_list
            return

        # switch chat thread
        self.post_message(CommandRequest(f"/thread switch {btn.id}"))

    async def on_command_request(self, event: CommandRequest) -> None:
        # Listen for /thread new command completion by monitoring thread list changes
        # This is handled by the parent UI, so nothing to do here
        pass

    async def thread_update(self, msg_thread: MessageThread):
        # Overridden to handle new thread activation
        is_new = self.threads.get(msg_thread.thread_id, None) is None
        if is_new:
            await self.add_thread(msg_thread)
            # Set as active and notify parent to switch view
            self.set_active(msg_thread.thread_id)
            self.post_message(self.NewChatActivated(msg_thread.thread_id))
        else:
            # check if thread name may have changed
            btn = self.buttons[msg_thread.thread_id]
            if msg_thread.name and msg_thread.name != str(btn.label):
                btn.label = msg_thread.name
