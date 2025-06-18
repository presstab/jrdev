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
from jrdev.ui.textual_events import TextualEvents

import logging
logger = logging.getLogger("jrdev")

CHAT_ADD_TOOLTIP = "Add file to chat context"
CHAT_REMOVE_TOOLTIP = "Remove file to chat context"
CODE_ADD_TOOLTIP = "Add file to code context"
CODE_REMOVE_TOOLTIP = "Remove file from code context"

class ContextButton(Button):
    """Custom button for context actions with toggle capability"""
    def __init__(
        self,
        add_label: str,
        remove_label: str,
        add_tooltip: str,
        remove_tooltip: str,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.add_label = add_label
        self.remove_label = remove_label
        self.add_tooltip = add_tooltip
        self.remove_tooltip = remove_tooltip
        self.is_add_mode = True
        self._update_display()

    def _update_display(self) -> None:
        """Update button appearance based on current mode"""
        self.label = self.add_label if self.is_add_mode else self.remove_label
        self.tooltip = self.add_tooltip if self.is_add_mode else self.remove_tooltip

    def set_mode(self, is_add_mode: bool) -> None:
        """Explicitly set the button mode"""
        self.is_add_mode = is_add_mode
        self._update_display()

    def toggle_mode(self) -> None:
        """Flip the current button mode"""
        self.is_add_mode = not self.is_add_mode
        self._update_display()

class DirectoryWidget(Widget):
    def __init__(self, core_app: Application, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.core_app = core_app
        self.directory_tree = FilteredDirectoryTree("./", core_app)
        self.button_add_chat_context = ContextButton(
            "+ Chat Ctx", "- Chat Ctx",
            CHAT_ADD_TOOLTIP, CHAT_REMOVE_TOOLTIP,
            id="add_chat_context_button",
            classes="sidebar_button"
        )
        self.button_add_code_context = ContextButton(
            "+ Code Ctx", "- Code Ctx",
            CODE_ADD_TOOLTIP, CODE_REMOVE_TOOLTIP,
            id="add_code_context_button",
            classes="sidebar_button"
        )
        self.button_refresh_directory = Button(
            label="\u27F3",
            id="refresh_directory_button",
            classes=""
        )
        self.ctx_buttons_active = False

    def compose(self) -> ComposeResult:
        with Vertical(id="directory_widget_container"):
            # Directory tree fills the remaining space
            yield self.directory_tree
            # Buttons take only the space they need vertically
            with Horizontal(id="directory_widget_buttons", classes="button_container"):
                yield self.button_refresh_directory
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
        for button in self.query(ContextButton):
            button.styles.width = "1fr"
            button.styles.height = 1
            button.styles.border = None

        self.button_refresh_directory.styles.border = None
        self.button_refresh_directory.styles.min_width = 3
        self.button_refresh_directory.styles.width = 3
        self.button_refresh_directory.styles.height = 1
        self.button_refresh_directory.tooltip = "Refresh Contents"

        # disable context buttons since they won't have anything selected
        self.button_add_code_context.disabled = True
        self.button_add_chat_context.disabled = True

    def update_highlights(self):
        self.directory_tree.update_indexed_paths()
        self.directory_tree.update_chat_context_paths()
        self.directory_tree.update_code_context_paths()

    def reload_highlights(self):
        self.update_highlights()
        self.directory_tree.refresh()

    def get_selected_file_rel_path(self):
        # get selected file from directory tree
        if not self.directory_tree.cursor_node or not self.directory_tree.cursor_node.data or not self.directory_tree.cursor_node.data.path:
            return None

        full_path = self.directory_tree.cursor_node.data.path

        if not full_path.is_file():
            # not a valid path shouldn't have gotten this far
            logger.error(f"get_selected_file_rel_path: {full_path} is not a valid file")
            return None

        # Get the relative path
        current_dir = os.getcwd()
        return os.path.relpath(full_path, current_dir)

    def _get_files_in_directory_recursively(self, directory_path: Path) -> list[str]:
        """Recursively get all files in a directory, ignoring common nuisance files/dirs."""
        filepaths = []
        # More comprehensive ignore list
        ignore_dirs = {".git", ".idea", ".vscode", ".jrdev", "__pycache__", "node_modules", ".venv", "build", "dist", ".eggs"}
        ignore_exts = {".pyc", ".pyo", ".pyd", ".log", ".swp", ".swo"}
        current_dir = os.getcwd()

        for root, dirs, files in os.walk(directory_path, topdown=True):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if Path(file).suffix in ignore_exts:
                    continue
                
                full_path = Path(root) / file
                try:
                    # Ensure we are not adding a directory
                    if full_path.is_file():
                        rel_path = os.path.relpath(full_path, current_dir)
                        filepaths.append(rel_path)
                except ValueError:
                    # This can happen on Windows if the path is on a different drive
                    logger.warning(f"Could not create relative path for {full_path}")
                    
        return filepaths

    @on(DirectoryTree.DirectorySelected)
    def handle_dir_selected(self, event: DirectoryTree.DirectorySelected):
        # Directory selected, context buttons enabled
        self.ctx_buttons_active = True
        self.button_add_chat_context.disabled = False
        self.button_add_code_context.disabled = False

        # Check if any file in the directory is in the contexts to set button mode
        dir_path = event.path
        files_in_dir = self._get_files_in_directory_recursively(dir_path)

        if not files_in_dir:
            # No files to add, so disable buttons and reset mode
            self.ctx_buttons_active = False
            self.button_add_chat_context.disabled = True
            self.button_add_code_context.disabled = True
            self.button_add_chat_context.set_mode(is_add_mode=True)
            self.button_add_code_context.set_mode(is_add_mode=True)
            return

        # If any file is in chat context, set to remove mode. Otherwise, add mode.
        is_any_in_chat_ctx = any(f in self.directory_tree.chat_context_paths for f in files_in_dir)
        self.button_add_chat_context.set_mode(is_add_mode=not is_any_in_chat_ctx)

        # If any file is in code context, set to remove mode. Otherwise, add mode.
        is_any_in_code_ctx = any(f in self.directory_tree.code_context_paths for f in files_in_dir)
        self.button_add_code_context.set_mode(is_add_mode=not is_any_in_code_ctx)

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

        # toggle button state
        self.button_add_chat_context.set_mode(is_add_mode=rel_path not in self.directory_tree.chat_context_paths)
        self.button_add_code_context.set_mode(is_add_mode=rel_path not in self.directory_tree.code_context_paths)

    @on(Button.Pressed, "#add_chat_context_button")
    def handle_chat_context_button(self):
        if not self.ctx_buttons_active:
            return

        # selection will clear after this so disable buttons
        self.button_add_code_context.disabled = True
        self.button_add_chat_context.disabled = True
        self.ctx_buttons_active = False

        selected_node = self.directory_tree.cursor_node
        if not selected_node or not selected_node.data:
            return
        
        selected_path = selected_node.data.path
        chat_thread: MessageThread = self.core_app.get_current_thread()
        
        files_to_process = []
        is_directory_op = False

        if selected_path.is_dir():
            files_to_process = self._get_files_in_directory_recursively(selected_path)
            is_directory_op = True
        elif selected_path.is_file():
            rel_path = self.get_selected_file_rel_path()
            if rel_path:
                files_to_process.append(rel_path)

        if not files_to_process:
            self.notify("No files to process.", severity="warning", timeout=2)
            return

        is_add_mode = self.button_add_chat_context.is_add_mode
        
        if is_add_mode:
            for file_path in files_to_process:
                chat_thread.add_new_context(file_path)
            count = len(files_to_process)
            item_name = os.path.basename(selected_path) if is_directory_op else files_to_process[0]
            msg = f"Added {count} file(s) from '{item_name}' to chat context."
        else: # remove mode
            removed_count = 0
            failed_files = []
            for file_path in files_to_process:
                if chat_thread.remove_context(file_path):
                    removed_count += 1
                else:
                    failed_files.append(os.path.basename(file_path))
            
            item_name = os.path.basename(selected_path) if is_directory_op else files_to_process[0]
            msg = f"Removed {removed_count} file(s) from '{item_name}' from chat context."
            if failed_files:
                msg += f" Failed to remove {len(failed_files)} (already sent)."
                logger.warning(f"Failed to remove files from chat context: {failed_files}")

        # Notify UI of update
        self.post_message(TextualEvents.ChatThreadUpdate(chat_thread.thread_id))
        self.reload_highlights()
        logger.info(msg)
        self.notify(msg, timeout=3)

    @on(Button.Pressed, "#add_code_context_button")
    def handle_code_context_button(self):
        if not self.ctx_buttons_active:
            return

        # selection will clear after this so disable buttons
        self.button_add_code_context.disabled = True
        self.button_add_chat_context.disabled = True
        self.ctx_buttons_active = False

        selected_node = self.directory_tree.cursor_node
        if not selected_node or not selected_node.data:
            return
        
        selected_path = selected_node.data.path
        
        files_to_process = []
        is_directory_op = False

        if selected_path.is_dir():
            files_to_process = self._get_files_in_directory_recursively(selected_path)
            is_directory_op = True
        elif selected_path.is_file():
            rel_path = self.get_selected_file_rel_path()
            if rel_path:
                files_to_process.append(rel_path)

        if not files_to_process:
            self.notify("No files to process.", severity="warning", timeout=2)
            return

        is_add_mode = self.button_add_code_context.is_add_mode
        
        if is_add_mode:
            for file_path in files_to_process:
                self.core_app.stage_code_context(file_path)
            count = len(files_to_process)
            item_name = os.path.basename(selected_path) if is_directory_op else files_to_process[0]
            msg = f"Staged {count} file(s) from '{item_name}' for /code."
        else: # remove mode
            removed_count = 0
            for file_path in files_to_process:
                if self.core_app.remove_staged_code_context(file_path):
                    removed_count += 1
            
            item_name = os.path.basename(selected_path) if is_directory_op else files_to_process[0]
            msg = f"Removed {removed_count} file(s) from '{item_name}' from staged code context."

        # Update highlights
        self.reload_highlights()
        logger.info(msg)
        self.notify(msg, timeout=3)

    @on(Button.Pressed, "#refresh_directory_button")
    def handle_refresh_directory_button(self):
        self.directory_tree.reload()
        self.notify("Directory refreshed", timeout=1)

class FilteredDirectoryTree(DirectoryTree):
    def __init__(self, path: str, core_app: Application):
        super().__init__(path)
        self.indexed_paths = []
        self.chat_context_paths = []
        self.code_context_paths = []
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

    def update_code_context_paths(self):
        self.code_context_paths = self.core_app.get_code_context()

    def render_label(self, node: TreeNode[DirEntry], base_style: Style, style: Style) -> Text:
        label = super().render_label(node, base_style, style)
        try:
            if node.data and node.data.path:
                try:
                    current_dir = os.getcwd()
                    abs_path = str(node.data.path)
                    relative_path = os.path.relpath(abs_path, current_dir)

                    if relative_path in self.indexed_paths:
                        label.stylize("italic green")
                    if relative_path in self.chat_context_paths:
                        label.stylize("italic blue")
                    if relative_path in self.code_context_paths:
                        label.stylize("italic red")

                except ValueError:
                    # todo Handle cases where paths are on different drives (Windows)
                    pass
        except ValueError:
            pass
        return label
