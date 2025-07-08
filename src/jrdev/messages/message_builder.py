import os
from typing import Dict, List, Set, Any
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.file_operations.file_utils import get_file_contents

import logging
# Get the global logger instance
logger = logging.getLogger("jrdev")


class MessageBuilder:
    def __init__(self, app: Any):
        self.app = app
        self.messages: List[Dict[str, str]] = []
        self.files: Set[str] = set()
        self.project_files: Set[str] = set()
        self.include_tree: bool = False
        self.file_aliases: Dict[str, str] = {}
        self.embedded_files: Set[str] = set()
        self.context: List[Dict[str, str]] = []
        self._current_user_content: List[str] = []
        self.isUserSectionFinal = False

    def add_system_message(self, content: str) -> None:
        """Add a system-level message to the conversation"""
        self.messages.insert(0, {"role": "system", "content": content})

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation"""
        self.messages.append({"role": "assistant", "content": content})

    def add_historical_messages(self, messages: List[Dict[str, str]]) -> None:
        """Add historical message chain"""
        self.messages.extend(messages)

    def add_file(self, file_path: str) -> None:
        """Queue a file to include in the message (prevents duplicates)"""
        if os.path.exists(file_path):
            if file_path not in self.embedded_files:
                self.files.add(file_path)
        else:
            logger.warning(f"File not found: {file_path}")

    def add_index_file(self, file_path: str, alias_path: str):
        """Add index files that will be added as 'Index of file alias_path' """
        self.file_aliases[file_path] = alias_path
        self.project_files.add(file_path)

    def set_embedded_files(self, files: Set[str]) -> None:
        """Set files that are already embedded within historical message thread as text. This prevents multiple files
        being added over and over"""
        self.embedded_files = files

    def get_files(self) -> Set[str]:
        return self.files

    def add_project_files(self) -> None:
        """Add all files from the terminal's project_files"""
        if self.app and hasattr(self.app.state, "project_files"):
            # Simple 10MB total size limit
            total_size_limit = 10 * 1024 * 1024  # Default 10MB limit
            current_size = 0
            
            # Add project files
            for file_path in self.app.state.project_files.values():
                # Skip files that would exceed the limit
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    if current_size + file_size > total_size_limit:
                        continue
                    current_size += file_size
                    self.project_files.add(file_path)
                
            # Add context files
            if hasattr(self.app, "state") and hasattr(self.app.state, "context_manager"):
                for aliases in self.app.state.context_manager.get_index_paths():
                    self.add_index_file(aliases[0], aliases[1])

    def add_tree(self):
        self.include_tree = True

    def add_context(self, context: List[str]) -> None:
        """Add context file paths to include in the message
        
        This method takes a list of file paths and adds them to the internal
        file list for later inclusion when finalizing the user section.
        """
        for file_path in context:
            self.add_file(file_path)

    def load_system_prompt(self, prompt_key: str) -> None:
        """Load and add a system prompt from PromptManager"""
        prompt = PromptManager.load(prompt_key)
        if prompt:
            self.add_system_message(prompt)

    def load_user_prompt(self, prompt_key: str) -> None:
        """Load and add a user prompt from PromptManager"""
        prompt = PromptManager.load(prompt_key)
        if prompt:
            self.append_to_user_section(prompt)

    def start_user_section(self, base_text: str = "") -> None:
        """Begin constructing a complex user message with files/context"""
        self._current_user_content = [base_text]

    def append_to_user_section(self, content: str) -> None:
        """Add content to the current user message section"""
        self._current_user_content.append(content)

    def _build_file_content(self) -> str:
        """Generate formatted file content section"""
        content = []
        # Add project files, including file tree
        if self.project_files or self.include_tree:
            # Load current file tree, with short explanation of how to read the format.
            # tree_explanation = PromptManager.load("init/filetree_format")
            # content.append(tree_explanation)
            file_tree = f"\n\n--- BEGIN FILE DIRECTORY ---\n{self.app.get_file_tree()}\n--- END FILE DIRECTORY ---\n"
            content.append(file_tree)

        for file_path in self.project_files:
            try:
                # mark indexes differently
                if file_path in self.file_aliases:
                    alias_path = self.file_aliases[file_path]
                    file_content = get_file_contents([file_path], alias_path)
                    content.append(file_content)
                else:
                    file_content = get_file_contents([file_path])
                    content.append(file_content)
            except Exception as e:
                logger.error(f"_build_file_content: Error reading {file_path}: {str(e)}")

        for file_path in self.files:
            try:
                # mark indexes differently
                file_content = get_file_contents([file_path])
                content.append(file_content)
            except Exception as e:
                logger.error(f"_build_file_content: Error reading {file_path}: {str(e)}")
        return "".join(content)


    def finalize_user_section(self) -> None:
        """Finalize and add the complex user message to messages"""
        full_content = f"{self._build_file_content()}"
        if self._current_user_content:
            full_content += "".join(self._current_user_content)

        self.add_user_message(full_content)
        self._current_user_content = []
        self.context.clear()
        self.isUserSectionFinal = True

    def clean(self) -> None:
        self.messages = [m for m in self.messages if m["content"] != ""]

    def build(self) -> List[Dict[str, str]]:
        """Return the fully constructed message list"""
        if not self.isUserSectionFinal:
            self.finalize_user_section()
        self.clean()
        return self.messages.copy()
