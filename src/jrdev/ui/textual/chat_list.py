from textual import events, on
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button
from typing import Dict, Optional
import logging

from jrdev.messages.thread import MessageThread

logger = logging.getLogger("jrdev")

class ChatList(Widget):

    def __init__(self, core_app, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.core_app = core_app
        self.buttons: Dict[str, Button] = {} # id -> Button
        self.threads: Dict[str, MessageThread] = {} # id -> MsgThread
        self.active_thread_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        for button in self.buttons.values():
            yield button

    async def on_mount(self) -> None:
        self.can_focus = False
        for button in self.buttons.values():
            button.can_focus = False
            button.styles.border = "none"
            button.styles.min_width = 4
            button.styles.width = "100%"
            button.styles.align_horizontal = "center"

    async def add_thread(self, msg_thread: MessageThread) -> None:
        tid = msg_thread.thread_id
        name = tid.removeprefix("thread_")
        btn = Button(label=name, id=tid, classes="sidebar_button")
        self.buttons[tid] = btn
        self.threads[tid] = msg_thread
        await self.mount(btn)
        # if this is the first thread, make it active
        if self.active_thread_id is None:
            self.set_active(tid)
        btn.can_focus = False
        btn.styles.border = "none"
        btn.styles.min_width = 4
        btn.styles.width = "100%"
        btn.styles.align_horizontal = "center"

    async def thread_update(self, msg_thread: MessageThread):
        # if this is a new thread, add it
        if self.threads.get(msg_thread.thread_id, None) is None:
            await self.add_thread(msg_thread)

    def set_active(self, thread_id: str) -> None:
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
        if btn.id not in self.buttons:
            # ignore button if it doesn't belong to chat_list
            return

        # switch chat thread
        if self.core_app.switch_thread(btn.id):
            self.set_active(btn.id)