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
                yield RichLog(id="diff-display", highlight=False, markup=True)
            
            with Horizontal(id="button-row"):
                yield Button("Yes", id="yes-button", variant="success", tooltip="Accept proposed changes")
                yield Button("No", id="no-button", variant="error", tooltip="Reject changes and end the current coding task")
                yield Button("Auto Accept", id="accept-all-button", variant="primary", tooltip="Automatically accepts all prompts for this code task")
                yield Button("Request Change", id="request-button", variant="warning", tooltip="Send an additional prompt that gives more guidance to the AI model")
                yield Button("Edit", id="edit-button", variant="primary", tooltip="Edit the generated code")
            
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

            # Format each line, stripping existing newlines and escaping Rich markup
            formatted_lines = []
            for line in self.diff_lines:
                # Skip None values
                if line is None:
                    continue

                # Strip trailing newlines
                line = line.rstrip('\n\r')

                # Escape Rich markup characters to prevent formatting issues
                escaped_line = line.replace("[", "\[").replace("]", "\]")

                # Format based on line prefix
                if line.startswith('+'):
                    formatted_lines.append(f"[green]{escaped_line}[/green]")
                elif line.startswith('-'):
                    formatted_lines.append(f"[red]{escaped_line}[/red]")
                else:
                    formatted_lines.append(escaped_line)

            # Join with newlines and write once
            diff_log.write("\n".join(formatted_lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        result = None
        
        if button_id == "yes-button":
            result = ("yes", None)
        elif button_id == "no-button":
            result = ("no", None)
        elif button_id == "edit-button":
            result = ("edit", None)
        elif button_id == "accept-all-button": # Handle Accept All button
            result = ("accept_all", None)
        elif button_id == "request-button":
            # Show the input field for request changes
            self.show_input = True
            self.query_one("#request-input").display = True
            self.query_one("#request-input").focus()
            return # Don't dismiss yet
            
        if result:
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
            
    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for confirmation dialog"""
        key = event.key
        result = None
        
        if key.lower() == "y":
            result = ("yes", None)
        elif key.lower() == "n":
            result = ("no", None)
        elif key.lower() == "e":
            result = ("edit", None)
        elif key.lower() == "a": # Handle 'a' key for Accept All
            result = ("accept_all", None)
        elif key.lower() == "r":
            # Show the input field for request changes
            self.show_input = True
            self.query_one("#request-input").display = True
            self.query_one("#request-input").focus()
            return # Don't dismiss yet
            
        if result:
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.show_input:
            # Only process input submission if the input is visible
            result = ("request_change", event.value)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
