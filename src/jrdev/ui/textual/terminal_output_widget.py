from textual import events, on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.document._document import Selection
from textual.widget import Widget
from textual.widgets import Label, Button, TextArea
from textual.color import Color
from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional
import logging
import pyperclip

logger = logging.getLogger("jrdev")

class TerminalOutputWidget(Widget):
    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.terminal_output = TextArea(id="terminal_output", language="plaintext")
        self.copy_button = Button(label="Copy Selection", id="copy_button")
        self.copy_button.on_click = self.copy_to_clipboard

    def compose(self) -> ComposeResult:
        yield self.terminal_output
        yield self.copy_button

    async def on_mount(self) -> None:
        self.can_focus = False
        self.terminal_output.can_focus = False
        self.copy_button.can_focus = False

        self.terminal_output.styles.border = "none"

        self.terminal_output.soft_wrap = True
        self.terminal_output.read_only = True
        self.terminal_output.show_line_numbers = False

    @on(Button.Pressed, "#copy_button")
    def handle_copy(self):
        self.copy_to_clipboard()

    def copy_to_clipboard(self) -> None:
        # Logic to copy the selected text of the TextArea to the clipboard
        if not self.terminal_output.text:
            return

        if self.terminal_output.selected_text:
            content = self.terminal_output.selected_text
        else:
            content = self.terminal_output.text
        # Use pyperclip to copy to clipboard
        pyperclip.copy(content)
        # Provide visual feedback
        self.notify("Text copied to clipboard", timeout=2)
        
    def append_text(self, text: str) -> None:
        """Append text to the end of the terminal output regardless of cursor position.
        
        This method preserves the current selection and auto-scrolls only if the
        scrollbar was already at the bottom before appending the text.
        
        Args:
            text: The text to append to the terminal output.
        """
        current_text = self.terminal_output.text
        current_selection = self.terminal_output.selection
        
        # Remember scroll position
        current_scroll = self.terminal_output.scroll_offset
        
        # Check if scroll is at the bottom before appending text
        # Get the scroll_y and document size to determine if we're at the bottom
        scroll_y = self.terminal_output.scroll_y
        content_size = self.terminal_output.document.get_size(4)  # 4 is a common tab width
        content_height = content_size.height
        viewport_height = self.terminal_output.size.height
        
        # Consider at bottom if scrolled to within a small margin of the end
        # or if all content fits in the viewport
        margin = 5  # Allow a small margin for rounding errors
        at_bottom = (scroll_y + viewport_height + margin >= content_height) or (content_height <= viewport_height)
        
        # Set the text with the new content appended
        new_text = current_text + text
        self.terminal_output.text = new_text
        
        # Restore the original selection if there was one
        if current_selection.start != current_selection.end:
            self.terminal_output.selection = current_selection
        else:
            # For an empty selection (just cursor), keep it where it was
            self.terminal_output.selection = Selection(current_selection.start, current_selection.start)
            
        # Auto-scroll to the end if we were at the bottom before, otherwise restore position
        if at_bottom:
            self.terminal_output.scroll_end(animate=False)
        else:
            self.terminal_output.scroll_to(x=current_scroll[0], y=current_scroll[1], animate=False)
        
        logger.info(f"highlights:\n{self.terminal_output._highlights}")
