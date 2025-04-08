from typing import Any, List, Optional, Tuple
from jrdev.ui.ui import PrintType

class UiWrapper:
    def __init__(self):
        self.ui_name = ""

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement print_text()")

    def print_stream(self, message: str):
        """print a stream of text"""
        raise NotImplementedError("Subclasses must implement print_stream()")
        
    async def prompt_for_confirmation(self, prompt_text: str = "Apply these changes?", diff_lines: Optional[List[str]] = None) -> Tuple[str, Optional[str]]:
        """
        Prompt the user for confirmation with options to apply, reject, request changes,
        or edit the changes.
        
        Args:
            prompt_text: The text to display when prompting the user
            diff_lines: Optional list of diff lines to display in the dialog
            
        Returns:
            Tuple of (response, message):
                - response: 'yes', 'no', 'request_change', or 'edit'
                - message: User's feedback message when requesting changes,
                          or edited content when editing, None otherwise
        """
        raise NotImplementedError("Subclasses must implement prompt_for_confirmation()")
        
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