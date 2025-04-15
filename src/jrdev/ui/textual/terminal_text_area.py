from textual.document._document import Selection
from textual.widgets import TextArea


class TerminalTextArea(TextArea):
    def __init__(self, id: str, language: str):
        super().__init__(id=id, language=language)

    def _watch_selection(
        self, previous_selection: Selection, selection: Selection
    ) -> None:
        return

    def append_text(self, text):
        current_text = self.text
        current_selection = self.selection

        # Determine if user is at or near the bottom before appending
        max_scroll = max(self.virtual_size.height - self.size.height, 0)
        current_scroll = self.scroll_y

        # Consider 'near the bottom' as within 2 lines of the bottom
        near_bottom_threshold = 4
        at_or_near_bottom = (max_scroll - current_scroll) <= near_bottom_threshold

        # Set the text with the new content appended
        new_text = current_text + text
        self.text = new_text

        # Restore the original selection if there was one
        if current_selection.start != current_selection.end:
            self.selection = current_selection
        else:
            # For an empty selection (just cursor), keep it where it was
            self.selection = Selection(current_selection.start, current_selection.start)

        # Only scroll to the bottom if the user was already at or near the bottom
        if at_or_near_bottom:
            self.scroll_y = max(self.virtual_size.height - self.size.height, 0)

        # Otherwise, keep scroll_y unchanged
        self.refresh()