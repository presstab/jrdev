import os
import asyncio
from typing import Any, Dict, List, Set, Optional

from jrdev.file_utils import JRDEV_DIR


class AppState:
    """Central class for managing application state"""

    def __init__(self):
        # Model configuration
        self.model: str = "deepseek-r1-671b"
        self.model_list: Any = None  # Will be initialized with ModelList

        # API clients
        self.clients: Any = None  # Will be initialized with APIClients

        # Message history
        self.messages: List[Dict[str, str]] = []
        self.files_in_history: Set[str] = set()

        # Context management
        self.context: List[str] = []
        self.use_project_context: bool = True
        self.project_files: Dict[str, str] = {
            "filetree": f"{JRDEV_DIR}jrdev_filetree.txt",
            "overview": f"{JRDEV_DIR}jrdev_overview.md",
            "conventions": f"{JRDEV_DIR}jrdev_conventions.md"
        }

        # Task management
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_monitor: Optional[asyncio.Task] = None

        # Runtime state
        self.running: bool = True
        self.need_first_time_setup: bool = False

    # Message history management
    def set_message_history(self, messages: List[Dict[str, str]], files: Set[str]) -> None:
        """Set the current message history and associated files"""
        self.messages = messages
        self.files_in_history = files

    def add_message_history(self, text: str, is_assistant: bool = False) -> None:
        """Add a message to the history"""
        role = "assistant" if is_assistant else "user"
        self.messages.append({"role": role, "content": text})

    def clear_messages(self) -> None:
        """Clear all message history"""
        self.messages.clear()
        self.files_in_history.clear()

    # Context management
    def add_context_file(self, file_path: str) -> None:
        """Add a file to the context list"""
        if file_path not in self.context:
            self.context.append(file_path)

    def clear_context(self) -> None:
        """Clear all context files"""
        self.context.clear()

    # Task management
    def add_task(self, task_id: str, task_info: Dict[str, Any]) -> None:
        """Register a background task"""
        self.active_tasks[task_id] = task_info

    def remove_task(self, task_id: str) -> None:
        """Remove a completed task"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    # State validation
    def validate(self) -> bool:
        """Check if critical state elements are initialized"""
        return all([
            self.model,
            self.project_files,
            self.model_list is not None,
            self.clients is not None
        ])

    def __repr__(self) -> str:
        return f"""<AppState:
Model: {self.model}
Messages: {len(self.messages)}
Context files: {len(self.context)}
Active tasks: {len(self.active_tasks)}
Clients initialized: {self.clients.is_initialized() if self.clients else False}
Running: {self.running}
>"""
