import logging
import re
from typing import Dict

from rich.text import Text
from textual import events
from textual.geometry import Offset
from textual.reactive import Reactive, reactive
from textual.widgets import TextArea

# Get the global logger instance
logger = logging.getLogger("jrdev")


class TerminalTextArea(TextArea):
    follow_tail: Reactive[bool] = reactive(True, init=True)  # replaces _auto_scroll
    _TOLERANCE = 1  # px / rows

    # compile a regex that captures what's inside the [...] after "PrintType="
    PATTERN = re.compile(r"\[PrintType=(.*?)]")

    def __init__(self, _id: str):
        # map of line index -> style name
        self._line_styles: Dict[int, str] = {}
        super().__init__(id=_id)
        self.cursor_blink = False
        # start in auto‑scroll mode
        self._auto_scroll = True

    def load_text(self, text: str) -> None:
        """
        Override load_text to pre-process the text, stripping tags and building a style map before loading to document
        """
        self._line_styles.clear()
        cleaned_lines = []

        if not text:
            super().load_text(text)
            return

        for line_index, line_content in enumerate(text.splitlines()):
            print_type, cleaned_line = self._extract_and_strip(line_content)
            if print_type:
                # store the style info for this line index
                self._line_styles[line_index] = print_type
            cleaned_lines.append(cleaned_line)

        super().load_text("\n".join(cleaned_lines))

    def get_line(self, line_index: int) -> Text:
        # grab the plain Rich.Text for this line
        line = super().get_line(line_index)

        print_type_str = self._line_styles.get(line_index)
        if print_type_str:
            # Get style from the central style manager
            style_str = self.app.jrdev.terminal_text_styles.styles.get(print_type_str, "white")
            line.stylize(style_str)

        # command highlight
        if line and line.plain.startswith("/"):
            space_idx = line.plain.find(" ")
            end = space_idx if space_idx >=0 else None
            line.stylize("bold blue", 0, end)

        return line

    def append_text(self, new_text: str) -> None:
        # First extract print_type info
        print_type, cleaned_text = self._extract_and_strip(new_text)
        idx_start = self.document.end[0]
        result = self.insert(cleaned_text, location=self.document.end)
        if print_type:
            idx_end = result.end_location[0]
            while idx_start <= idx_end:
                self._line_styles[idx_start] = print_type
                idx_start += 1
        self.call_after_refresh(lambda: self.scroll_end(animate=False) if self.follow_tail else None)

    # ---------- helpers -------------------------------------------------
    def _extract_and_strip(self, line: str) -> tuple[str | None, str]:
        """
        Returns (print_type, cleaned_line).
        print_type is the type the tag, or None if no tag.
        cleaned_line is the original text with the entire '[PrintType=…]' removed.
        """
        m = self.PATTERN.search(line)
        if not m:
            return None, line

        # now remove ALL occurrences of '[PrintType=…]'
        print_type = m.group(1)
        cleaned = self.PATTERN.sub("", line)
        return print_type, cleaned

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

    def scroll_cursor_visible(self, center: bool = False, animate: bool = False) -> Offset:
        return Offset()
