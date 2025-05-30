from textual.color import Color
from typing import Optional
import logging

from jrdev.ui.tui.input_widget import CommandTextArea

logger = logging.getLogger("jrdev")

class ChatInputWidget(CommandTextArea):
    """A specialized input widget for chat interactions."""
    
    DEFAULT_CSS = """
    ChatInputWidget {
        background: $surface;
        color: $foreground;
        border: tall $border-blurred;
        width: 100%;
        height: 3;  /* Default to 3 lines of height */
        scrollbar-size: 1 1;

        &:focus {
            border: tall $border;
        }

        & .text-area--cursor {
            background: $input-cursor-background;
            color: $input-cursor-foreground;
            text-style: $input-cursor-text-style;
        }
    }
    """
    
    def __init__(
            self,
            placeholder: str = "Enter message",
            id: str = "chat_input",
            height: int = 3,
            **kwargs
    ):
        """Initialize the ChatInputWidget.
        
        Args:
            placeholder: Optional placeholder text shown when empty.
            id: The ID of the widget.
            height: The height of the widget in lines (default: 3).
            **kwargs: Additional arguments to pass to CommandTextArea.
        """
        super().__init__(placeholder=placeholder, id=id, height=height, **kwargs)
        self.border_title = "Chat Input"
        self.styles.border = ("round", Color.parse("#5e5e5e"))
        self.styles.border_title_color = "#fabd2f"
