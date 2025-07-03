import logging

from textual import events
from textual.geometry import Offset
from textual.reactive import Reactive, reactive
from textual.widgets import TextArea

# Get the global logger instance
logger = logging.getLogger("jrdev")


class TerminalTextArea(TextArea):
    follow_tail: Reactive[bool] = reactive(True, init=True)  # replaces _auto_scroll
    _TOLERANCE = 1  # px / rows

    def __init__(self, _id: str, language: str):
        super().__init__(id=_id, language=language)
        self.cursor_blink = False
        # start in auto‑scroll mode
        self._auto_scroll = True

    # ---------- helpers -------------------------------------------------
    def _is_at_bottom(self) -> bool:
        max_scroll = max(self.virtual_size.height - self.size.height, 0)
        return self.scroll_y >= max_scroll - self._TOLERANCE

    def _after_any_scroll(self) -> None:
        """Run after *every* wheel / key / drag to (re)arm follow-tail."""
        self.follow_tail = self._is_at_bottom()  # True *or* False

    # ---------- event hooks ---------------------------------------------
    def _watch_scroll_y(self) -> None:
        super()._watch_scroll_y()
        self._after_any_scroll()

    async def _on_key(self, event: events.Key) -> None:
        await super()._on_key(event)
        # arrow‐up/down, page‐up/down are also manual scroll triggers
        if event.key in ("up", "down", "pageup", "pagedown"):
            self._after_any_scroll()

    def append_text(self, new_text: str) -> None:
        self.insert(new_text, location=self.document.end)
        self.call_after_refresh(lambda: self.scroll_end(animate=False) if self.follow_tail else None)

    def scroll_cursor_visible(self, center: bool = False, animate: bool = False) -> Offset:
        return Offset()
