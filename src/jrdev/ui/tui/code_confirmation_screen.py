from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, RichLog
from textual.containers import Vertical, Horizontal
from typing import Any, Generator, List, Optional, Tuple
import asyncio

class CodeConfirmationScreen(ModalScreen[Tuple[str, Optional[str]]]):
    """Modal screen for confirmation dialogs"""

    DEFAULT_CSS = """
    CodeConfirmationScreen {
        align: center middle;
    }

    #confirmation-dialog {
        width: 80%;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: round $accent;
        padding: 0;
        layout: vertical;
    }

    #prompt-header {
        dock: top;
        height: 3;
        padding: 0 1;
        border-bottom: solid $accent;
        width: 100%;
    }

    #prompt-text {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #main-content {
        width: 100%;
        height: 1fr;
        padding: 1;
        overflow: hidden;
    }

    #error-message-label {
        width: 100%;
        padding: 1;
        content-align: center middle;
        text-align: center;
        margin-bottom: 1;
    }

    #diff-display {
        background: $surface-darken-1;
        border: round $panel;
        padding: 0 1;
        /* Scrollbar styles from textual_ui.py global styles are expected to apply */
    }
    
    #request-input-container {
        width: 100%;
        padding: 1;
        background: $surface;
        border-top: solid $panel;
        display: none; /* Initially hidden */
        height: auto;
    }

    #request-input {
        width: 100%;
    }

    #button-footer {
        dock: bottom;
        height: auto;
        min-height: 3;
        padding: 1;
        border-top: solid $accent;
        width: 100%;
        align-horizontal: center;
    }

    #button-footer > Button {
        margin: 0 1;
        border: none;
    }
    """
    
    def __init__(self, prompt_text: str, diff_lines: Optional[List[str]] = None, error_msg: Optional[str] = None) -> None:
        super().__init__()
        self.prompt_text = prompt_text
        self.diff_lines = diff_lines or []
        self.error_msg = error_msg
        self.input_value = ""
        self.show_input = False
        self.future = None  # Will be set by the JrDevUI class
        
    def compose(self) -> Generator[Any, None, None]:
        with Vertical(id="confirmation-dialog"):
            with Horizontal(id="prompt-header"):
                yield Label(self.prompt_text, id="prompt-text")
            
            with Vertical(id="main-content"):
                if self.error_msg:
                    error_display_text = f"[bold red]Error: {self.error_msg}\nClick No to cancel the task.[/bold red]"
                    yield Label(error_display_text, id="error-message-label", markup=True)
                if self.diff_lines:
                    yield RichLog(id="diff-display", highlight=False, markup=True)
            
            with Vertical(id="request-input-container"):
                yield Input(placeholder="Enter your requested changes...", id="request-input")

            with Horizontal(id="button-footer"):
                yield Button("Yes", id="yes-button", variant="success", tooltip="Accept proposed changes")
                yield Button("No", id="no-button", variant="error", tooltip="Reject changes and end the current coding task")
                yield Button("Auto Accept", id="accept-all-button", variant="primary", tooltip="Automatically accepts all prompts for this code task")
                yield Button("Request Change", id="request-button", variant="warning", tooltip="Send an additional prompt that gives more guidance to the AI model")
                yield Button("Edit", id="edit-button", variant="primary", tooltip="Edit the generated code")

    def on_mount(self) -> None:
        """Setup the screen on mount"""
        self.query_one("#request-input-container").display = False

        if self.diff_lines:
            diff_log = self.query_one("#diff-display")
            diff_log.height = min(20, len(self.diff_lines) + 2)  # Set a reasonable max height for the diff log

            formatted_lines = []
            for line in self.diff_lines:
                if line is None:
                    continue
                line = line.rstrip('\n\r')
                escaped_line = line.replace("[", "\[")
                if line.startswith('+'):
                    formatted_lines.append(f"[green]{escaped_line}[/green]")
                elif line.startswith('-'):
                    formatted_lines.append(f"[red]{escaped_line}[/red]")
                else:
                    formatted_lines.append(escaped_line)
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
        elif button_id == "accept-all-button":
            result = ("accept_all", None)
        elif button_id == "request-button":
            self.show_input = True
            self.query_one("#request-input-container").display = True
            self.query_one("#request-input").focus()
            return
            
        if result:
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
            
    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for confirmation dialog"""
        key = event.key
        result = None
        
        if self.query_one("#request-input-container").display and event.key == "escape":
            self.query_one("#request-input-container").display = False
            self.show_input = False
            # Potentially focus a default button or the dialog itself
            self.query_one("#yes-button").focus()
            return

        if self.show_input and self.query_one("#request-input").has_focus:
            # If input is active, don't process general shortcuts like 'y', 'n' etc.
            # except for 'escape' handled above or 'enter' (handled by on_input_submitted)
            return

        if key.lower() == "y":
            result = ("yes", None)
        elif key.lower() == "n":
            result = ("no", None)
        elif key.lower() == "e":
            result = ("edit", None)
        elif key.lower() == "a":
            result = ("accept_all", None)
        elif key.lower() == "r":
            self.show_input = True
            self.query_one("#request-input-container").display = True
            self.query_one("#request-input").focus()
            return
            
        if result:
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.show_input:
            result = ("request_change", event.value)
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
