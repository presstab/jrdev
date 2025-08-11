import asyncio
import os
import logging
from collections import deque
from typing import Deque, Optional

from textual.app import ComposeResult
from textual.widget import Widget
from textual.containers import Vertical
from textual.color import Color

from jrdev.file_operations.file_utils import JRDEV_DIR
from jrdev.ui.tui.terminal.terminal_text_area import TerminalTextArea

logger = logging.getLogger("jrdev")


class LogViewWidget(Widget):
    """
    A widget that tails the application's log file and displays only the last 100 lines.
    - Maintains a fixed-size buffer (deque maxlen=100) to minimize memory usage.
    - Periodically refreshes the display with the current buffer to avoid storing full history.
    - Uses TerminalTextArea for read-only, follow-tail behavior and styling of PrintType tags if present.
    """

    DEFAULT_MAX_LINES = 100

    def __init__(self, core_app=None, id: Optional[str] = None, max_lines: int = DEFAULT_MAX_LINES) -> None:
        super().__init__(id=id)
        self.core_app = core_app
        self.max_lines = max_lines
        self._lines: Deque[str] = deque(maxlen=self.max_lines)
        self._last_rendered_text: str = ""
        self._tail_task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._update_timer = None

        # UI elements
        self.layout_output: Optional[Vertical] = None
        self.text_area: Optional[TerminalTextArea] = None

    # -------------- composition ------------------
    def compose(self) -> ComposeResult:
        # Outer bordered container exposed as `layout_output` so parent can set border title
        self.layout_output = Vertical(id="log_view_container")
        self.text_area = TerminalTextArea(_id="log_text_area")
        self.text_area.read_only = True
        self.text_area.can_focus = False

        # Provide an initial hint until the file is read
        self.text_area.load_text("Waiting for log updates...\n")

        # Build tree: container -> text_area
        with self.layout_output:
            yield self.text_area

    # -------------- lifecycle ------------------
    async def on_mount(self) -> None:
        # Give a default border title; parent app may override on switch
        if self.layout_output:
            self.layout_output.border_title = "Logs"
            self.layout_output.styles.border = ("round", Color.parse("#5e5e5e"))
            self.layout_output.styles.border_title_color = "#fabd2f"
            self.text_area.styles.border = "none"
            self.text_area.styles.margin = 0
            self.text_area.styles.padding = 0

        self._stop_event = asyncio.Event()
        # Timer to refresh UI from buffer at a sane cadence
        self._update_timer = self.set_interval(0.5, self._refresh_view, pause=False)
        # Background tailing task
        self._tail_task = asyncio.create_task(self._tail_log_file())

    async def on_unmount(self) -> None:
        if self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()
        if self._tail_task:
            try:
                await asyncio.wait_for(self._tail_task, timeout=1.0)
            except Exception:
                # best-effort cancellation
                self._tail_task.cancel()
        if self._update_timer:
            self._update_timer.stop()

    # -------------- log tailing ------------------
    def _log_path(self) -> str:
        # Log file is JRDEV_DIR + 'jrdev.log'
        return os.path.join(JRDEV_DIR, "jrdev.log")

    async def _tail_log_file(self) -> None:
        """
        Tails the log file, keeping only the last `max_lines` and updating the deque as new lines arrive.
        Handles file not found, truncation, and rotation by retrying and reopening as needed.
        """
        path = self._log_path()
        f = None
        current_inode = None

        try:
            while self._stop_event and not self._stop_event.is_set():
                # Wait for the file to exist
                if not os.path.exists(path):
                    await asyncio.sleep(0.5)
                    continue

                try:
                    # Open if not open or rotated
                    if f is None:
                        f = open(path, "r", encoding="utf-8", errors="replace")
                        try:
                            current_inode = os.fstat(f.fileno()).st_ino
                        except Exception:
                            current_inode = None

                        # Prime buffer with the last N lines efficiently
                        # Reading as a stream ensures we don't load full file into memory
                        self._prime_buffer(f)
                        # Seek to end for tailing new lines
                        f.seek(0, os.SEEK_END)

                    # Read new lines as they are written
                    line = f.readline()
                    if not line:
                        # No new data; check for rotation/truncation
                        await asyncio.sleep(0.3)

                        # Detect truncation
                        try:
                            st = os.stat(path)
                            if f.tell() > st.st_size:
                                # Truncated; reopen and re-prime
                                f.close()
                                f = None
                                continue
                        except FileNotFoundError:
                            # Rotated away
                            f.close()
                            f = None
                            continue

                        # Detect rotation by inode change
                        try:
                            st_inode = os.stat(path).st_ino
                            if current_inode is not None and st_inode != current_inode:
                                f.close()
                                f = None
                                continue
                        except FileNotFoundError:
                            # Rotated away
                            if f:
                                f.close()
                                f = None
                            continue

                        continue

                    # We have a new line
                    self._lines.append(line)

                except Exception as e:
                    logger.debug(f"LogViewWidget tail loop error: {e}")
                    # Back-off briefly on error and retry
                    await asyncio.sleep(0.5)
                    # Force reopen on next loop
                    if f:
                        try:
                            f.close()
                        except Exception:
                            pass
                        f = None

        finally:
            if f:
                try:
                    f.close()
                except Exception:
                    pass

    def _prime_buffer(self, file_obj) -> None:
        """Fill the deque with up to the last max_lines from file_obj without keeping full history in memory."""
        try:
            # Stream lines into a temporary deque; this does not load the whole file into memory
            temp = deque(file_obj, maxlen=self.max_lines)
            self._lines.clear()
            self._lines.extend(temp)
        except Exception as e:
            logger.debug(f"Failed to prime log buffer: {e}")
            self._lines.clear()

    # -------------- UI refresh ------------------
    def _refresh_view(self) -> None:
        if not self.text_area:
            return
        # Join without creating long-lived references; only last 100 lines are present
        text = "".join(self._lines)
        if text == self._last_rendered_text:
            return
        self._last_rendered_text = text
        # Replace full content to avoid retaining history in TextArea document
        self.text_area.load_text(text)
        # Follow tail if at bottom
        if getattr(self.text_area, "follow_tail", True):
            self.text_area.call_after_refresh(lambda: self.text_area.scroll_end(animate=False))
