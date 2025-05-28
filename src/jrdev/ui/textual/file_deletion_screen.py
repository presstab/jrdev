from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal
from typing import Generator, Any
import os

class FileDeletionScreen(ModalScreen[bool]):
    """Modal screen for file deletion confirmation"""

    DEFAULT_CSS = """
    FileDeletionScreen {
        align: center middle;
    }

    #deletion-dialog {
        width: 60%;
        height: auto;
        max-height: 50%;
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
        padding: 2 1;
        overflow: hidden;
    }

    #warning-label {
        width: 100%;
        content-align: center middle;
        text-align: center;
        margin-bottom: 1;
        color: $warning;
        text-style: bold;
    }

    #file-path-label {
        width: 100%;
        content-align: center middle;
        text-align: center;
        margin-bottom: 2;
        color: $text;
        background: $surface-darken-1;
        border: round $panel;
        padding: 1;
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
        margin: 0 2;
        border: none;
        min-width: 12;
    }
    """
    
    def __init__(self, filepath: str) -> None:
        super().__init__()
        self.filepath = filepath
        self.future = None  # Will be set by the JrDevUI class
        
    def compose(self) -> Generator[Any, None, None]:
        with Vertical(id="deletion-dialog"):
            with Horizontal(id="prompt-header"):
                yield Label("Delete File", id="prompt-text")
            
            with Vertical(id="main-content"):
                yield Label("WARNING: This action cannot be undone!", id="warning-label", markup=True)
                
                # Show file path and whether it exists
                file_display = f"Delete this file?\n\n[bold]{self.filepath}[/bold]"
                yield Label(file_display, id="file-path-label", markup=True)

            with Horizontal(id="button-footer"):
                yield Button("Cancel", id="cancel-button", variant="default", tooltip="Cancel deletion and keep the file")
                yield Button("Delete", id="delete-button", variant="error", tooltip="Permanently delete this file")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        result = None
        
        if button_id == "delete-button":
            result = True
        elif button_id == "cancel-button":
            result = False
            
        if result is not None:
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)
            
    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for deletion dialog"""
        key = event.key.lower()
        result = None
        
        if key == "d":
            result = True
        elif key in ("c", "n", "escape"):
            result = False
            
        if result is not None:
            if self.future:
                self.future.set_result(result)
            self.dismiss(result)