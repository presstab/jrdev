from jrdev.ui.ui import terminal_print, PrintType
from jrdev.ui.ui_wrapper import UiWrapper
from typing import Any, List, Optional, Tuple

class CliEvents(UiWrapper):
    def __init__(self):  # Add app reference
        super().__init__()
        self.ui_name = "cli"

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        # Post custom message when print is called
        terminal_print(message, print_type, end, prefix, flush)

    def print_stream(self, message: str):
        """print a stream of text"""
        terminal_print(message, PrintType.LLM, end="", flush=True)
        
    async def prompt_for_confirmation(self, prompt_text: str = "Apply these changes?", diff_lines: Optional[List[str]] = None) -> Tuple[str, Optional[str]]:
        """
        Prompt the user for confirmation with options to apply, reject, request changes,
        or edit the changes in a text editor.
        
        Args:
            prompt_text: The text to display when prompting the user
            diff_lines: Optional list of diff lines (not used in CLI as diff is already displayed)
            
        Returns:
            Tuple of (response, message):
                - response: 'yes', 'no', 'request_change', or 'edit'
                - message: User's feedback message when requesting changes,
                          or edited content when editing, None otherwise
        """
        while True:
            response = input(f"\n{prompt_text} ✅ Yes [y] | ❌ No [n] | 🔄 Request Change [r] | ✏️  Edit [e]: ").lower().strip()
            if response in ('y', 'yes'):
                return 'yes', None
            elif response in ('n', 'no'):
                return 'no', None
            elif response in ('r', 'request', 'request_change'):
                self.print_text("Please enter your requested changes:", PrintType.INFO)
                message = input("> ")
                return 'request_change', message
            elif response in ('e', 'edit'):
                self.print_text("Opening editor... (Ctrl+S/Alt+W to save, Ctrl+Q/Alt+Q/ESC to quit)", PrintType.INFO)
                return 'edit', None
            else:
                self.print_text("Please enter 'y', 'n', 'r', or 'e'", PrintType.ERROR)