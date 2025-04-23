import asyncio
import uuid
import os
import json
from typing import Any, Dict, List, Optional, Set

from jrdev.file_utils import JRDEV_DIR
from jrdev.messages.thread import MessageThread


class AppState:
    """Central class for managing application state"""

    def __init__(self) -> None:
        # Load persisted chat model or fallback to default
        config_path = os.path.join(JRDEV_DIR, "model_profiles.json")
        loaded_model = None
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    data = json.load(f)
                    loaded_model = data.get("chat_model")
        except Exception:
            loaded_model = None
        # Use loaded model or default
        self.model: str = loaded_model if loaded_model else "deepseek-r1-671b"

        # Model list and profiles (initialized later)
        self.model_list: Any = None  # Will be initialized with ModelList
        self.model_profile_manager = None

        # API clients
        self.clients: Any = None  # Will be initialized with APIClients

        # Thread management
        self.active_thread: str = "main"
        self.threads: Dict[str, MessageThread] = {
            "main": MessageThread("main")
        }

        # Context management
        self.context_code: Set[str] = set()
        self.use_project_context: bool = True
        self.project_files: Dict[str, str] = {
            "overview": f"{JRDEV_DIR}jrdev_overview.md",
            "conventions": f"{JRDEV_DIR}jrdev_conventions.md",
        }

        # Task management
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_monitor: Optional[asyncio.Task[None]] = None

        # Runtime state
        self.running: bool = True
        self.need_first_time_setup: bool = False
        self.need_api_keys: bool = False

    # Message thread management
    def get_current_thread(self) -> MessageThread:
        """Get the currently active message thread"""
        return self.threads[self.active_thread]

    # Thread management
    def create_thread(self, thread_id: str="") -> str:
        """Create a new message thread"""
        if thread_id == "":
            thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        if thread_id not in self.threads:
            self.threads[thread_id] = MessageThread(thread_id)
        return thread_id

    def switch_thread(self, thread_id: str) -> bool:
        """Switch to a different thread"""
        if thread_id in self.threads:
            self.active_thread = thread_id
            return True
        return False

    # Code Command Context
    def stage_code_context(self, file_path) -> None:
        """Stage files that will be added as context to the next /code command"""
        self.context_code.add(file_path)

    def get_code_context(self) -> Set[str]:
        """Files that are staged for code command"""
        return self.context_code

    def clear_code_context(self) -> None:
        """Clear staged code context"""
        self.context_code.clear()

    def remove_staged_code_context(self, file_path) -> bool:
        """Remove staged code context"""
        if file_path not in self.context_code:
            return False
        self.context_code.remove(file_path)
        return True

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
        return all(
            [
                self.model,
                self.project_files,
                self.model_list is not None,
                self.clients is not None,
            ]
        )

    def __repr__(self) -> str:
        thread = self.get_current_thread()
        return f"<AppState:\nModel: {self.model}\nActive thread: {self.active_thread}\nThread count: {len(self.threads)}\nMessages in thread: {len(thread.messages)}\nContext files: {len(self.context_code)}\nActive tasks: {len(self.active_tasks)}\nClients initialized: {self.clients.is_initialized() if self.clients else False}\nRunning: {self.running}\n>"
