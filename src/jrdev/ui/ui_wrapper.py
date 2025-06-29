from typing import Any, Dict, List, Optional, Tuple
from jrdev.ui.ui import PrintType

class UiWrapper:
    def __init__(self):
        self.ui_name = ""
        self.capture_active = False
        self.capture = ""

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement print_text()")

    def print_stream(self, message: str):
        """print a stream of text"""
        raise NotImplementedError("Subclasses must implement print_stream()")

    def stream_chunk(self, thread_id: str, chunk: str) -> None:
        """
        Handle an incoming chunk of text from a streaming LLM response.
        
        Args:
            thread_id: The ID of the conversation thread this chunk belongs to.
            chunk: The piece of text from the AI's response.
        """
        raise NotImplementedError("Subclasses must implement stream_chunk()")

    def start_capture(self) -> None:
        self.capture_active = True
        self.capture = ""

    def end_capture(self) -> None:
        self.capture_active = False

    def get_capture(self) -> str:
        return self.capture
        
    async def prompt_for_confirmation(self, prompt_text: str = "Apply these changes?", diff_lines: Optional[List[str]] = None, error_msg: str = None) -> Tuple[str, Optional[str]]:
        """
        Prompt the user for confirmation with options to apply, reject, request changes,
        edit the changes, or accept all subsequent changes.
        
        Args:
            prompt_text: The text to display when prompting the user
            diff_lines: Optional list of diff lines to display in the dialog
            error_msg: Optional error message to display if something has failed on a previous attempt
            
        Returns:
            Tuple of (response, message):
                - response: 'yes', 'no', 'request_change', 'edit', or 'accept_all'
                - message: User's feedback message when requesting changes,
                          or edited content when editing, None otherwise
        """
        raise NotImplementedError("Subclasses must implement prompt_for_confirmation()")

    async def prompt_steps(self, steps: Any) -> Any:
        """
        Prompt the user to confirm, edit, reprompt, accept all, or cancel the steps.
        Args:
            steps: The steps JSON object (dict)
        Returns:
            dict with keys:
                - 'choice': One of 'accept', 'edit', 'reprompt', 'accept_all', 'cancel'.
                - 'steps': The (potentially edited) steps JSON object (if choice is 'accept', 'edit', or 'accept_all').
                - 'prompt': The user's additional prompt text (if choice is 'reprompt').
        """
        raise NotImplementedError("Subclasses must implement prompt_steps")
        
    async def signal_exit(self):
        """
        Signal to the UI that it should exit the application
        
        This method is called when the application needs to shut down.
        Each UI implementation should handle this appropriately.
        """
        raise NotImplementedError("Subclasses must implement signal_exit()")

    async def signal_no_keys(self):
        """
        Signal to the UI that no api keys have been detected

        This method is called when the application is first started
        """
        raise NotImplementedError("Subclasses must implement signal_no_keys")

    def model_changed(self, model):
        """
        Signal to the UI that a new model has been selected
        """
        raise NotImplementedError("Subclasses must implement model_changed")

    def model_list_updated(self) -> None:
        """
        Signal to the UI that the list of models has changed
        """
        raise NotImplementedError("Subclasses must implement model_list_updated")

    def chat_thread_update(self, thread_id):
        """
        Signal to the UI that a chat thread has been updated
        """
        raise NotImplementedError("Subclasses must implement chat_thread_update")

    def code_context_update(self):
        """
        Signal to the UI that code context has been updated
        """
        raise NotImplementedError("Subclasses must implement code_context_update")

    def update_task_info(self, worker_id: str, update: dict = None) -> None:
        """
        Send updates to the UI about worker task
        Args:
            worker_id:
            update: mutable dict containing any kind of updates to parse
        """
        raise NotImplementedError("Subclasses must implement update_task_info")

    def project_context_changed(self, is_enabled: bool) -> None:
        """Project Context has been toggled on or off"""
        raise NotImplementedError("Subclasses must implement project_context_changed")

    def providers_updated(self) -> None:
        """The list of providers has been updated (add/edit/delete)"""
        raise NotImplementedError("Subclasses must implement providers_updated")

    async def prompt_for_deletion(self, filepath: str) -> bool:
        """
        Prompt the user for confirmation before deleting a file.
        
        Args:
            filepath: The path to the file that will be deleted
            
        Returns:
            bool: True if the user confirms deletion, False otherwise
        """
        raise NotImplementedError("Subclasses must implement prompt_for_deletion")
