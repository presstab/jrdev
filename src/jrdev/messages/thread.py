'''Message thread implementation.'''

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from jrdev.file_operations.file_utils import JRDEV_DIR

THREADS_DIR = os.path.join(JRDEV_DIR, "threads")
os.makedirs(THREADS_DIR, exist_ok=True)

USER_INPUT_PREFIX = "User Input: "

def auto_persist(fn):
    """Decorator to automatically persist thread state after a method call."""
    def wrapper(self, *args, **kwargs):
        result = fn(self, *args, **kwargs)
        try:
            self.save()
        except Exception as e:
            # Optionally log with jrdev.logger or handle specific exceptions
            # For now, failing silently as per the initial sketch's pass
            # print(f"Error during auto-persist for {fn.__name__}: {e}") # For debugging
            pass
        return result
    return wrapper

class MessageThread:
    """Thread for storing a sequence of messages and related context."""

    def __init__(self, thread_id: str):
        """Initialize a new message thread.

        Args:
            thread_id: Unique identifier for this thread
        """
        self.thread_id: str = thread_id
        self.name: Optional[str] = None
        self.messages: List[Dict[str, str]] = []
        self.context: Set[str] = set()
        self.embedded_files: Set[str] = set()
        self.token_usage: Dict[str, int] = {"input": 0, "output": 0}
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now(),
            "last_modified": datetime.now(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert the thread's state to a serializable dictionary."""
        return {
            "thread_id": self.thread_id,
            "name": self.name,
            "messages": self.messages,
            "context": list(self.context),
            "embedded_files": list(self.embedded_files),
            "token_usage": self.token_usage,
            "metadata": {
                "created_at": self.metadata["created_at"].isoformat(),
                "last_modified": self.metadata["last_modified"].isoformat(),
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageThread':
        """Create a MessageThread instance from a dictionary."""
        thread = cls(data["thread_id"])
        thread.name = data.get("name")
        thread.messages = data.get("messages", [])
        thread.context = set(data.get("context", []))
        thread.embedded_files = set(data.get("embedded_files", []))
        thread.token_usage = data.get("token_usage", {"input": 0, "output": 0})
        metadata_dict = data.get("metadata", {})
        thread.metadata = {
            "created_at": datetime.fromisoformat(metadata_dict.get("created_at", datetime.now().isoformat())),
            "last_modified": datetime.fromisoformat(metadata_dict.get("last_modified", datetime.now().isoformat())),
        }
        return thread

    def save(self) -> None:
        """Save the thread's state to a JSON file."""
        file_path = os.path.join(THREADS_DIR, f"{self.thread_id}.json")
        tmp_file_path = file_path + ".tmp"
        try:
            with open(tmp_file_path, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            os.replace(tmp_file_path, file_path)
        except Exception as e:
            # Optionally log this error
            # print(f"Error saving thread {self.thread_id}: {e}") # For debugging
            if os.path.exists(tmp_file_path):
                try:
                    os.remove(tmp_file_path)
                except OSError:
                    pass # Failed to remove temp file
            raise # Re-raise the exception if saving is critical

    def delete_persisted_file(self) -> None:
        """Delete the persisted JSON file for this thread."""
        file_path = os.path.join(THREADS_DIR, f"{self.thread_id}.json")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as e:
            # Optionally log this error
            # print(f"Error deleting persisted file {file_path}: {e}") # For debugging
            pass

    @auto_persist
    def set_name(self, new_name: str) -> None:
        """Set or update the name of the thread."""
        self.name = new_name
        self.metadata["last_modified"] = datetime.now()

    @auto_persist
    def add_new_context(self, file_path: str) -> None:
        """Add a new file that will be embedded into the next sent message in this thread."""
        self.context.add(file_path)
        self.metadata["last_modified"] = datetime.now()

    @auto_persist
    def remove_context(self, file_path: str) -> bool:
        """Remove a file from the context."""
        if file_path not in self.context:
            return False
        self.context.remove(file_path)
        self.metadata["last_modified"] = datetime.now()
        return True

    def get_context_paths(self) -> List[str]:
        """Returns current relative file paths in the thread's context (including embedded)."""
        context_paths = []
        for p in self.context:
            context_paths.append(p)
        for p in self.embedded_files:
            if p not in context_paths:
                context_paths.append(p)
        return context_paths

    @auto_persist
    def add_embedded_files(self, files: List[str]) -> None:
        """After a message is sent, the active context files become embedded."""
        for file_path in files:
            self.embedded_files.add(file_path)
            if file_path in self.context:
                self.context.remove(file_path)
        self.metadata["last_modified"] = datetime.now()

    @auto_persist
    def add_response(self, response: str) -> None:
        """Add a complete assistant response to the thread history."""
        self.messages.append({"role": "assistant", "content": response})
        self.metadata["last_modified"] = datetime.now()

    @auto_persist
    def add_response_partial(self, chunk: str) -> None:
        """Add a partial assistant response chunk to the thread history."""
        if self.messages and self.messages[-1].get("role") == "assistant":
            self.messages[-1]["content"] += chunk
        else:
            self.messages.append({"role": "assistant", "content": chunk})
        self.metadata["last_modified"] = datetime.now()

    @auto_persist
    def finalize_response(self, full_text: str) -> None:
        """Finalize the assistant response, replacing partials with full text."""
        if self.messages and self.messages[-1].get("role") == "assistant":
            self.messages[-1]["content"] = full_text
        else:
            self.messages.append({"role": "assistant", "content": full_text})
        self.metadata["last_modified"] = datetime.now()

    @auto_persist
    def set_compacted(self, messages: List[Dict[str, str]]) -> None:
        """Replace the existing messages list and reset file states."""
        self.messages = messages
        self.context = set()
        self.embedded_files = set()
        self.metadata["last_modified"] = datetime.now()
