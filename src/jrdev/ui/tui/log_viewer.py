import asyncio
import os
from collections import deque
from textual.widgets import ListView, ListItem, Label
from textual import work
from jrdev.file_operations.file_utils import JRDEV_DIR

LOG_FILE = os.path.join(JRDEV_DIR, "jrdev.log")
MAX_LINES = 100

class LogViewer(ListView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._lines = deque(maxlen=MAX_LINES)
        self._log_file_handle = None
        self._worker = None

    def on_mount(self):
        self._worker = self.tail_log()

    def on_unmount(self):
        if self._worker:
            self._worker.cancel()
        if self._log_file_handle:
            self._log_file_handle.close()

    @work
    async def tail_log(self):
        if not os.path.exists(LOG_FILE):
            self.append(ListItem(Label(f"Log file not found: {LOG_FILE}")))
            return

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            self._log_file_handle = f
            # Go to the end of the file
            f.seek(0, os.SEEK_END)
            while self.is_running:
                line = f.readline()
                if line:
                    self.add_line(line)
                else:
                    await asyncio.sleep(0.1)

    def add_line(self, line: str):
        self._lines.append(line.strip())
        self.clear()
        for line_text in self._lines:
            self.append(ListItem(Label(line_text)))
        self.scroll_end()
