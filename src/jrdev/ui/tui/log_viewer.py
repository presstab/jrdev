import asyncio
import os
from collections import deque

from textual.widgets import RichLog
from textual import work

from jrdev.file_operations.file_utils import JRDEV_DIR

LOG_FILE = os.path.join(JRDEV_DIR, "jrdev.log")


class LogViewer(RichLog):
    """A widget to view and tail a log file."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs, id="log_viewer", wrap=True, markup=True)
        self._lines = deque(maxlen=100)

    def on_mount(self) -> None:
        """Start tailing the log file when the widget is mounted."""
        self.clear()
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                # Read all lines and the deque will keep the last 100
                self._lines.extend(f.readlines())
                self.write("".join(self._lines))
        else:
            self.write(f"Log file not found at {LOG_FILE}")

        self.tail_log_file()

    @work
    async def tail_log_file(self) -> None:
        """Tail the log file."""
        if not os.path.exists(LOG_FILE):
            return

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            # Go to the end of the file
            f.seek(0, os.SEEK_END)

            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue

                self._lines.append(line)

                # This is not ideal as it clears and rewrites everything
                # but it's the simplest way to enforce the 100 line limit
                # with a deque. RichLog doesn't have a way to remove the first line.
                self.clear()
                self.write("".join(self._lines))
