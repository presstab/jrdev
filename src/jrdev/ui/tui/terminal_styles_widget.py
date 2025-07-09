import logging
from typing import Any, Dict

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Label, Input

from jrdev.ui.ui import PrintType, printtype_to_string

logger = logging.getLogger("jrdev")

class TerminalStylesWidget(Widget):
    """Widget for managing terminal text styles."""

    DEFAULT_CSS = """
    TerminalStylesWidget {
        align: center middle;
    }

    #styles-container {
        width: 100%;
        max-width: 120;
        height: 100%;
        background: $surface;
        border: none;
        padding: 0;
        margin: 0;
        layout: vertical;
    }

    #styles-list-scrollable-container {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
        overflow-x: hidden;
    }

    .style-row {
        layout: horizontal;
        height: auto;
        margin-bottom: 1;
        align: center middle;
    }

    .style-label {
        width: 20%;
        color: $text-muted;
        text-align: right;
        margin-right: 2;
    }

    .style-input {
        width: 70%;
        border: none;
        height: 1;
        &:focus {
            border: none;
            background-tint: $foreground 5%;
        }
    }

    #save-styles-button-container {
        dock: bottom;
        height: 3;
        align: center middle;
        padding: 1 0;
    }
    
    #save-styles-button-container Button {
        width: 20;
        border: none;
    }
    """

    def __init__(self, core_app: Any, **kwargs):
        super().__init__(**kwargs)
        self.core_app = core_app
        self.style_inputs: Dict[str, Input] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="styles-container"):
            with ScrollableContainer(id="styles-list-scrollable-container"):
                all_print_types = list(PrintType)
                current_styles = self.core_app.terminal_text_styles.styles

                for print_type in all_print_types:
                    print_type_str = printtype_to_string(print_type)
                    style_value = current_styles.get(print_type_str, "")
                    
                    with Horizontal(classes="style-row"):
                        yield Label(f"{print_type_str}:", classes="style-label")
                        input_widget = Input(
                            value=style_value,
                            id=f"style-input-{print_type_str}",
                            classes="style-input"
                        )
                        self.style_inputs[print_type_str] = input_widget
                        yield input_widget
            
            with Vertical(id="save-styles-button-container"):
                yield Button("Save Styles", id="btn-save-styles", variant="success")

    @on(Button.Pressed, "#btn-save-styles")
    def handle_save_styles(self) -> None:
        """Save the updated styles to the core application and persist them."""
        styles_manager = self.core_app.terminal_text_styles
        
        # Update styles from input fields
        for print_type_str, input_widget in self.style_inputs.items():
            # The key in style_inputs is already the string representation of PrintType
            styles_manager.styles[print_type_str] = input_widget.value

        # Persist the changes by calling the app's method
        self.core_app.write_terminal_text_styles()
        
        self.notify("Terminal styles saved.", severity="information", timeout=4)

        # Refresh the terminal output to show new styles
        try:
            terminal_text_area = self.app.query_one("#terminal_output")
            terminal_text_area.refresh(layout=True)
        except Exception as e:
            logger.error(f"Could not refresh terminal text area after style change: {e}")
