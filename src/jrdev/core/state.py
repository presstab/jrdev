import asyncio
import uuid
import os
import json
from typing import Any, Dict, List, Optional, Set

from jrdev.file_operations.file_utils import JRDEV_DIR
from jrdev.messages.thread import MessageThread


class AppState:
    """Central class for managing application state"""

    def __init__(self, persisted_threads: Optional[Dict[str, MessageThread]] = None, ui_mode = None) -> None:
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
        self.active_thread = ""
        self.router_thread_id: str = ""
        if persisted_threads:
            self.threads: Dict[str, MessageThread] = persisted_threads
            if ui_mode and ui_mode == "cli":
                # for cli, look for an empty chat thread on init and use that as current
                for thread in self.threads.values():
                    if not thread.messages:
                        self.active_thread = thread.thread_id
                        break
                # if no empty chat, then create new
                if not self.active_thread:
                    self.active_thread = self.create_thread()
            else:
                # for Textual UI choose the most recently modified thread as the current thread
                user_threads = {
                    tid: t for tid, t in self.threads.items()
                }
                if user_threads:
                    latest = max(
                        user_threads.values(),
                        key=lambda t: t.metadata["last_modified"],
                    )
                    self.active_thread = latest.thread_id
                else:
                    self.active_thread = self.create_thread()
        else:
            self.threads: Dict[str, MessageThread] = {}
            self.active_thread = self.create_thread()

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

    def get_active_thread_id(self) -> str:
        return self.active_thread

    def get_thread_ids(self) -> List[str]:
        return list(self.threads.keys())

    def get_thread(self, thread_id) -> Optional[MessageThread]:
        """Get a message thread instance"""
        return self.threads.get(thread_id)

    def get_all_threads(self) -> List[MessageThread]:
        """Get all message thread instances"""
        return list(self.threads.values())

    # Thread management
    def create_thread(self, thread_id: str="", meta_data: Dict[str, str]=None) -> str:
        """Create a new message thread"""
        if thread_id == "":
            thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        if thread_id not in self.threads:
            # New threads should also be saved immediately if persistence is active
            # This is handled by @auto_persist on MessageThread methods like set_name or if it's saved on creation
            # For now, MessageThread constructor doesn't auto-save, so an explicit save might be needed
            # or ensure first mutation triggers save. The current design relies on mutation.
            self.threads[thread_id] = MessageThread(thread_id)
            if meta_data:
                for k, v in meta_data.items():
                    self.threads[thread_id].metadata[k] = v
        return thread_id

    def switch_thread(self, thread_id: str) -> bool:
        """Switch to a different thread"""
        if thread_id in self.threads:
            self.active_thread = thread_id
            return True
        return False

    def reset_router_thread(self):
        """Clear messages and context of router thread"""
        if self.router_thread_id in self.threads:
            router_thread = self.threads[self.router_thread_id]
            router_thread.messages = []
            router_thread.context.clear()

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

    # Delete thread command support
    def delete_thread(self, thread_id: str) -> bool:
        """Delete an existing message thread and adjust active thread if needed"""
        if thread_id not in self.threads:
            return False
        
        thread_to_delete = self.threads.get(thread_id)
        if thread_to_delete:
            thread_to_delete.delete_persisted_file() # Remove persisted file

        # Remove the thread from runtime
        del self.threads[thread_id]
        
        # Adjust active_thread if necessary
        if self.active_thread == thread_id:
            if self.threads: # If other threads exist, switch to the first one
                self.active_thread = next(iter(self.threads))
            else: # No threads left create new
                self.active_thread = self.create_thread()
        return True

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
        return f"<AppState:\nModel: {self.model}\nActive thread: {self.active_thread}\nThread count: {len(self.threads)}\nMessages in thread: {len(thread.messages) if thread else 'N/A'}\nContext files: {len(self.context_code)}\nActive tasks: {len(self.active_tasks)}\nClients initialized: {self.clients.is_initialized() if self.clients else False}\nRunning: {self.running}\n>"
