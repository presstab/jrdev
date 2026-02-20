from textual import on
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, Tree
from textual.widgets.tree import TreeNode
from textual.message import Message
from typing import Dict, List, Optional, Any
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

    DEFAULT_CSS = """
    ChatList {
        layout: vertical;
        width: 100%;
        height: 100%;
    }
    #new_thread {
        dock: top;
        width: 100%;
        height: 3;
        min-height: 3;
        margin-bottom: 1;
    }
    Tree {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    """

    def __init__(self, core_app, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.core_app = core_app
        # We need to map thread_id to TreeNode to easily find/update them
        self.thread_nodes: Dict[str, TreeNode] = {}
        self.category_nodes: Dict[str, TreeNode] = {}
        self.threads: Dict[str, MessageThread] = {} # id -> MsgThread
        self.active_thread_id: Optional[str] = None
        self.new_button = Button(label="+ New Chat", id="new_thread", classes="sidebar_button")
        self.tree = Tree("Chats")
        self.tree.show_root = False
        self.tree.guide_depth = 2

    def compose(self) -> ComposeResult:
        yield self.new_button
        yield self.tree

    async def on_mount(self) -> None:
        self.new_button.can_focus = False
        self.tree.focus() # Let the tree take focus for navigation
        pass

    async def add_thread(self, msg_thread: MessageThread) -> None:
        # filter out any router threads
        thread_type = msg_thread.metadata.get("type")
        if thread_type and thread_type == "router":
            return

        tid = msg_thread.thread_id
        is_new = tid not in self.threads
        self.threads[tid] = msg_thread

        category = getattr(msg_thread, "category", "default") or "default"

        # Find or create category node
        if category not in self.category_nodes:
            # Add category node
            cat_node = self.tree.root.add(category, expand=True)
            self.category_nodes[category] = cat_node
        else:
            cat_node = self.category_nodes[category]

        name = tid.removeprefix("thread_")
        if msg_thread.name:
            name = msg_thread.name

        # Add thread node or update
        if tid in self.thread_nodes:
            node = self.thread_nodes[tid]
            # Check if parent matches (category change)
            if node.parent != cat_node:
                node.remove()
                # Re-add in correct category
                thread_node = cat_node.add_leaf(name, data=tid)
                self.thread_nodes[tid] = thread_node
                # Reselect if active
                if self.active_thread_id == tid:
                    self.tree.select_node(thread_node)
            else:
                # Just update label
                if str(node.label) != name:
                    node.label = name
        else:
            thread_node = cat_node.add_leaf(name, data=tid)
            self.thread_nodes[tid] = thread_node
            # If this is active (e.g. loaded on startup), select it
            if self.active_thread_id == tid:
                self.tree.select_node(thread_node)

        # if this is the first thread and none active, make it active
        if self.active_thread_id is None:
            self.set_active(tid)

        if is_new and self.active_thread_id == tid:
             self.tree.select_node(self.thread_nodes[tid])


    def check_threads(self, all_threads: List[str]) -> None:
        # check our list of threads against the list from app state
        to_remove = [tid for tid in self.threads.keys() if tid not in all_threads]
        for tid in to_remove:
            if tid in self.thread_nodes:
                self.thread_nodes[tid].remove()
                del self.thread_nodes[tid]

            self.threads.pop(tid, None)
            if self.active_thread_id == tid:
                self.active_thread_id = None

        # Optional: Cleanup empty categories
        cats_to_remove = []
        for cat, node in self.category_nodes.items():
            if not node.children:
                node.remove()
                cats_to_remove.append(cat)
        for cat in cats_to_remove:
            del self.category_nodes[cat]

    def set_active(self, thread_id: str) -> None:
        # if this is already active thread, then ignore
        if self.active_thread_id == thread_id:
            return

        self.active_thread_id = thread_id
        if thread_id in self.thread_nodes:
            self.tree.select_node(self.thread_nodes[thread_id])

    @on(Button.Pressed, "#new_thread")
    async def handle_new_thread_click(self, event: Button.Pressed):
        self.post_message(CommandRequest("/thread new"))

    @on(Tree.NodeSelected)
    async def handle_tree_selection(self, event: Tree.NodeSelected):
        node = event.node
        if node.data:
            # It's a thread node
            thread_id = node.data
            if thread_id != self.active_thread_id:
                self.post_message(CommandRequest(f"/thread switch {thread_id}"))
        else:
            # Category node, toggle expansion
            node.toggle()

    async def thread_update(self, msg_thread: MessageThread):
        # Overridden to handle new thread activation or updates
        is_new = self.threads.get(msg_thread.thread_id, None) is None
        await self.add_thread(msg_thread)

        if is_new:
            # Set as active and notify parent to switch view
            self.set_active(msg_thread.thread_id)
            self.post_message(self.NewChatActivated(msg_thread.thread_id))
