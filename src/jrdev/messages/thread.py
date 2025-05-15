'''Message thread implementation.'''

from datetime import datetime
from typing import Any, Dict, List, Optional, Set


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

    def add_new_context(self, file_path):
        """Add a new file that will be embedded into the next sent message in this thread"""
        # this does not check if the file is already embedded!
        self.context.add(file_path)
        self.metadata["last_modified"] = datetime.now()

    def remove_context(self, file_path) -> bool:
        if file_path not in self.context:
            return False
        self.context.remove(file_path)
        return True

    def get_context_paths(self):
        """Returns current relative file paths in the thread's context (including embedded)"""
        context_paths = []
        for p in self.context:
            context_paths.append(p)
        for p in self.embedded_files:
            if p not in context_paths:
                context_paths.append(p)
        return context_paths

    def add_embedded_files(self, files):
        """After a message is sent, the active context files become embedded into a previous message"""
        for file in files:
            self.embedded_files.add(file)
            if file in self.context:
                self.context.remove(file)
        self.metadata["last_modified"] = datetime.now()

    def add_response(self, response):
        self.messages.append({"role": "assistant", "content": response})
        self.metadata["last_modified"] = datetime.now()

    def add_response_partial(self, chunk: str) -> None:
        """Add a partial assistant response chunk to the thread history."""
        if self.messages and self.messages[-1].get("role") == "assistant":
            self.messages[-1]["content"] += chunk
        else:
            self.messages.append({"role": "assistant", "content": chunk})
        self.metadata["last_modified"] = datetime.now()

    def finalize_response(self, full_text: str) -> None:
        """Finalize the assistant response, replacing partials with full text."""
        if self.messages and self.messages[-1].get("role") == "assistant":
            self.messages[-1]["content"] = full_text
        else:
            # This case should ideally not happen if add_response_partial was called first
            # but as a fallback, we add a new message.
            self.messages.append({"role": "assistant", "content": full_text})
        self.metadata["last_modified"] = datetime.now()

    def set_compacted(self, messages):
        """Replace the exising messages list, set file states to default"""
        self.messages = messages
        self.context = set()
        self.embedded_files = set()
        self.metadata["last_modified"] = datetime.now()
