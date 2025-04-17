from textual.document._document import Selection
from textual.geometry import Offset
from textual.widgets import TextArea
from textual import events

from textual.document._document import Selection

import logging
# Get the global logger instance
logger = logging.getLogger("jrdev")

class TerminalTextArea(TextArea):

    def __init__(self, id: str, language: str):
        super().__init__(id=id, language=language)
        # start in auto‑scroll mode
        self._auto_scroll = True

    def _on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self._auto_scroll = False
        super()._on_mouse_scroll_up(event)

    def _on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self._auto_scroll = False
        super()._on_mouse_scroll_down(event)

    def _on_key(self, event: events.Key) -> None:
        # arrow‐up/down, page‐up/down are also manual scroll triggers
        if event.key in ("up", "down", "pageup", "pagedown"):
            self._auto_scroll = False
        super()._on_key(event)

    def append_text(self, new_text: str) -> None:
        # 1) Remember where we were
        prev_scroll = self.scroll_y

        # 2) Insert in‑place so we don't reload the document
        end = self.document.end
        self.insert(new_text, location=end)

        # 3) After the document actually re‑flows, either
        #    a) go to the bottom if we are still in auto‑scroll mode
        #    b) restore the exact scroll position if not
        def adjust_scroll():
            max_scroll = max(self.virtual_size.height - self.size.height, 0)
            if self._auto_scroll:
                # still in auto‑scroll mode → always jump to bottom
                self.scroll_y = max_scroll
            else:
                # manual‑scroll mode → put them back exactly where they were
                # (but clamp into [0, max_scroll])
                self.scroll_y = min(prev_scroll, max_scroll)

        self.call_after_refresh(adjust_scroll)

        # 4) And force a redraw
        self.refresh()

        # 5) If we *were* at the bottom before we inserted, we can
        #    re‑enable auto‑scroll for next time.  Otherwise leave it off.
        max_scroll = max(self.virtual_size.height - self.size.height, 0)
        if prev_scroll >= max_scroll - 1:
            self._auto_scroll = True

    def scroll_cursor_visible(
        self, center: bool = False, animate: bool = False
    ) -> Offset:
        return Offset()