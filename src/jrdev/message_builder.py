import os
from typing import Dict, List, Set, Optional, Any
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.file_utils import get_file_contents
from jrdev.ui.ui import terminal_print, PrintType


class MessageBuilder:
    def __init__(self, terminal: Optional[Any] = None):
        self.messages: List[Dict[str, str]] = []
        self.files: Set[str] = set()
        self.context: List[Dict[str, str]] = []
        self.terminal = terminal
        self._current_user_content: List[str] = []

    def add_system_message(self, content: str) -> None:
        """Add a system-level message to the conversation"""
        self.messages.append({"role": "system", "content": content})

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation"""
        self.messages.append({"role": "assistant", "content": content})

    def add_file(self, file_path: str) -> None:
        """Queue a file to include in the message (prevents duplicates)"""
        if os.path.exists(file_path):
            self.files.add(file_path)
        else:
            terminal_print(f"File not found: {file_path}", PrintType.WARNING)

    def add_project_files(self) -> None:
        """Add all files from the terminal's project_files"""
        if self.terminal and hasattr(self.terminal, "project_files"):
            for file_path in self.terminal.project_files.values():
                self.add_file(file_path)

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

    def start_user_section(self, base_text: str = "") -> None:
        """Begin constructing a complex user message with files/context"""
        self._current_user_content = [base_text]

    def append_to_user_section(self, content: str) -> None:
        """Add content to the current user message section"""
        self._current_user_content.append(content)

    def _build_file_content(self) -> str:
        """Generate formatted file content section"""
        content = []
        for file_path in self.files:
            try:
                file_content = get_file_contents([file_path])
                content.append(
                    f"\n\n{os.path.basename(file_path).upper()}:\n{file_content}"
                )
            except Exception as e:
                terminal_print(
                    f"Error reading {file_path}: {str(e)}", PrintType.WARNING
                )
        return "".join(content)

    def _build_context_section(self) -> str:
        """Generate formatted context section"""
        if not self.context:
            return ""

        context_section = "\n\nUSER CONTEXT:"
        for i, ctx in enumerate(self.context):
            context_section += f"\n--- Context File {i + 1}: {ctx.get('name', '')} ---\n{ctx.get('content', '')}\n"
        return context_section

    def finalize_user_section(self) -> None:
        """Finalize and add the complex user message to messages"""
        if not self._current_user_content:
            return

        full_content = "".join(self._current_user_content)
        full_content += self._build_file_content()
        full_content += self._build_context_section()

        self.add_user_message(full_content)
        self._current_user_content = []
        self.files.clear()
        self.context.clear()

    def build(self) -> List[Dict[str, str]]:
        """Return the fully constructed message list"""
        return self.messages.copy()
