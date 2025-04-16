from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, RichLog
from textual.containers import Vertical, Horizontal
from typing import Any, Generator, List, Optional, Tuple
import asyncio

class CodeConfirmationScreen(ModalScreen[Tuple[str, Optional[str]]]):
    """Modal screen for confirmation dialogs"""
    
    def __init__(self, prompt_text: str, diff_lines: Optional[List[str]] = None) -> None:
        super().__init__()
        self.prompt_text = prompt_text
        self.diff_lines = diff_lines or []
        self.input_value = ""
        self.show_input = False
        self.future = None  # Will be set by the JrDevUI class
        
    def compose(self) -> Generator[Any, None, None]:
        with Vertical(id="confirmation-dialog"):
            yield Label(self.prompt_text, id="prompt-text")
            
            # Display the diff if we have it
            if self.diff_lines:
                yield RichLog(id="diff-display", highlight=True, markup=True)
            
            with Horizontal(id="button-row"):
                yield Button("Yes [y]", id="yes-button", variant="success")
                yield Button("No [n]", id="no-button", variant="error")
                yield Button("Request Change [r]", id="request-button", variant="warning")
                yield Button("Edit [e]", id="edit-button", variant="primary")
            
            # Create the input but we'll hide it in on_mount
            yield Input(placeholder="Enter your requested changes...", id="request-input")
    
    def on_mount(self) -> None:
        """Setup the screen on mount"""
        # Hide the input field initially
        self.query_one("#request-input").display = False
        
        # Add the diff lines to the RichLog if we have them
        if self.diff_lines:
            diff_log = self.query_one("#diff-display")
            diff_log.height = min(15, len(self.diff_lines) + 2)  # Set a reasonable height
            
            # Add each line with appropriate coloring
            for line in self.diff_lines:
                if line.startswith('+'):
                    diff_log.write(f"[green]{line}[/green]")
                elif line.startswith('-'):
                    diff_log.write(f"[red]{line}[/red]")
                else:
                    diff_log.write(line)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        if button_id == "yes-button":
            result = ("yes", None)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
        elif button_id == "no-button":
            result = ("no", None)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
        elif button_id == "edit-button":
            result = ("edit", None)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
        elif button_id == "request-button":
            # Show the input field for request changes
            self.show_input = True
            self.query_one("#request-input").display = True
            self.query_one("#request-input").focus()
            
    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for confirmation dialog"""
        key = event.key
        if key.lower() == "y":
            result = ("yes", None)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
        elif key.lower() == "n":
            result = ("no", None)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
        elif key.lower() == "e":
            result = ("edit", None)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
        elif key.lower() == "r":
            # Show the input field for request changes
            self.show_input = True
            self.query_one("#request-input").display = True
            self.query_one("#request-input").focus()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.show_input:
            # Only process input submission if the input is visible
            result = ("request_change", event.value)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)