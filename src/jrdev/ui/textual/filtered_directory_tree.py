import os
from pathlib import Path
from typing import Iterable, Any, Optional

from rich.style import Style
from rich.text import Text
from textual import on
from textual.await_complete import AwaitComplete
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, DirectoryTree
from textual.widgets._directory_tree import DirEntry
from textual.widgets._tree import TreeNode
from textual.app import ComposeResult

from jrdev.core.application import Application
from jrdev.messages import MessageThread

import logging
logger = logging.getLogger("jrdev")

CHAT_ADD_TOOLTIP = "Add file to chat context"
CHAT_REMOVE_TOOLTIP = "Remove file to chat context"

class DirectoryWidget(Widget):
    def __init__(self, core_app: Application, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.core_app = core_app
        self.directory_tree = FilteredDirectoryTree("./", core_app)
        self.button_add_chat_context = Button("+ Chat Ctx", id="add_chat_context_button", classes="sidebar_button", tooltip=CHAT_ADD_TOOLTIP)
        self.button_add_chat_context.is_add_mode = True
        self.button_add_code_context = Button("+ Code Ctx", id="add_code_context_button", classes="sidebar_button", tooltip="Add file to code context")
        self.ctx_buttons_active = False

    def compose(self) -> ComposeResult:
        with Vertical(id="directory_widget_container"):
            # Directory tree fills the remaining space
            yield self.directory_tree
            # Buttons take only the space they need vertically
            with Horizontal(id="directory_widget_buttons", classes="button_container"):
                yield self.button_add_chat_context
                yield self.button_add_code_context

    async def on_mount(self) -> None:
        self.can_focus = False
        # Let the parent container determine the overall height
        self.styles.height = "auto"
        # Configure the internal layout
        self.query_one("#directory_widget_buttons").styles.height = "auto"
        self.directory_tree.styles.height = "1fr" # Fill available vertical space within the widget
        self.directory_tree.styles.width = "100%" # Fill available horizontal space

        # Apply consistent styling to buttons within this widget
        for button in self.query(Button):
            button.styles.width = "1fr"
            button.styles.height = 1
            button.styles.border = None

        # disable context buttons since they won't have anything selected
        self.button_add_code_context.disabled = True
        self.button_add_chat_context.disabled = True

    def update_highlights(self):
        self.directory_tree.update_indexed_paths()
        self.directory_tree.update_chat_context_paths()

    def get_selected_file_rel_path(self):
        # get selected file from directory tree
        if not self.directory_tree.cursor_node.data or not self.directory_tree.cursor_node.data.path:
            return None

        full_path = self.directory_tree.cursor_node.data.path

        # Get the relative path
        current_dir = os.getcwd()
        return os.path.relpath(full_path, current_dir)

    @on(DirectoryTree.DirectorySelected)
    def handle_dir_selected(self):
        # contexts buttons cannot add a directory
        self.ctx_buttons_active = False
        self.button_add_chat_context.disabled = True
        self.button_add_code_context.disabled = True

    @on(DirectoryTree.FileSelected)
    def handle_file_selected(self):
        # file selected, context buttons enabled
        self.ctx_buttons_active = True
        self.button_add_chat_context.disabled = False
        self.button_add_code_context.disabled = False

        # if the file is in the chat context, show it as remove mode
        if not self.ctx_buttons_active:
            return

        rel_path = self.get_selected_file_rel_path()
        if not rel_path:
            return

        if rel_path in self.directory_tree.chat_context_paths:
            self.button_add_chat_context.label = "- Chat Ctx"
            self.button_add_chat_context.tooltip = CHAT_REMOVE_TOOLTIP
            self.button_add_chat_context.is_add_mode = False
        else:
            self.button_add_chat_context.label = "+ Chat Ctx"
            self.button_add_chat_context.tooltip = CHAT_ADD_TOOLTIP
            self.button_add_chat_context.is_add_mode = True

    @on(Button.Pressed, "#add_chat_context_button")
    def handle_chat_context_button(self):
        if not self.ctx_buttons_active:
            return

        rel_path = self.get_selected_file_rel_path()
        if not rel_path:
            return

        chat_thread: MessageThread = self.core_app.get_current_thread()
        msg = f"Added {rel_path} to message thread: {chat_thread.thread_id}"
        if self.button_add_chat_context.is_add_mode:
            chat_thread.add_new_context(rel_path)
        else:
            if not chat_thread.remove_context(rel_path):
                msg = f"Failed to remove {rel_path}. Files sent in previous messages cannot be removed."
                logger.info(msg)
                self.notify(msg, timeout=2)
                # update just in case
                self.update_highlights()
                return
            msg = f"Removed {rel_path} from message thread: {chat_thread.thread_id}"

        # Update highlights
        self.update_highlights()

        # Show notification
        logger.info(msg)
        self.notify(msg, timeout=2)

        self.directory_tree.reload()

    @on(Button.Pressed, "#add_code_context_button")
    def handle_code_context_button(self):
        if not self.ctx_buttons_active:
            return

        rel_path = self.get_selected_file_rel_path()
        if not rel_path:
            return

        # todo no current way to add context to code command yet

class FilteredDirectoryTree(DirectoryTree):
    def __init__(self, path: str, core_app: Application):
        super().__init__(path)
        self.indexed_paths = []
        self.chat_context_paths = []
        self.core_app = core_app
        self.state = core_app.state

    """Filter out jrdev directory"""
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not (path.name.startswith("jrdev") and not path.parent.name.startswith("src"))]

    def reload(self) -> AwaitComplete:
        self.update_indexed_paths()
        return super().reload()

    def update_indexed_paths(self):
        indexed_paths = self.state.context_manager.get_file_paths()
        if indexed_paths:
            self.indexed_paths = indexed_paths

    def update_chat_context_paths(self):
        chat_thread:MessageThread = self.core_app.get_current_thread()
        self.chat_context_paths = chat_thread.get_context_paths()

    def render_label(self, node: TreeNode[DirEntry], base_style: Style, style: Style) -> Text:
        label = super().render_label(node, base_style, style)
        root_path = self.PATH(self.path)
        try:
            sub_paths = []
            if node.data and node.data.path:
                # climb the tree to create relative path
                n = node
                while n:
                    sub_paths.insert(0, n.data.path.name)
                    n = n.parent
                relative_path = node.data.path.name
                if sub_paths:
                    relative_path = f"{os.path.join(*sub_paths)}"

                # add styling for indexed files
                if relative_path in self.indexed_paths:
                    label.stylize("italic green")
                if relative_path in self.chat_context_paths:
                    label.stylize("italic blue")
        except ValueError:
            pass
        return label