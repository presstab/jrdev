from typing import Optional

from textual.widgets import DataTable, Label
from textual.color import Color
from textual.worker import Worker, WorkerState
import logging
import time
logger = logging.getLogger("jrdev")


class TaskMonitor(DataTable):

    def __init__(self):
        super().__init__()
        self.column_names = ["id", "task", "model", "tok_in", "tok_out", "tok/sec", "runtime", "status"]
        self.row_key_workers = {} # {row_key: worker.name}
        self.runtimes = {} # {worker.name: start_time}
        self.update_timer = None
        self.tracked_commands = [
            "init",
            "code",
            "chat",
            "asyncsend",
            "git pr review",
            "git pr summary"
        ]

    async def on_mount(self) -> None:
        self.border_title = "Tasks"
        self.styles.border = ("round", Color.parse("#63f554"))
        for column in self.column_names:
            if column == "model":
                self.add_column(column, key=column, width=16)
            else:
                self.add_column(column, key=column)

    def truncate_cell_content(self, content: str, max_width: int) -> str:
        return content if len(content) <= max_width else content[:max_width - 1] + "…"

    def add_task(self, task_id: str, task_name: str, model: str, sub_task_name: Optional[str] = None) -> None:
        if not sub_task_name and not task_name.startswith("/"):
            task_name = "chat"
        use_name = task_name
        if sub_task_name:
            use_name = sub_task_name
        use_name = self.truncate_cell_content(use_name, 20)
        row = (task_id, use_name, model, 0, 0, 0, 0, "active")
        row_key = self.add_row(*row, key=task_id)
        self.row_key_workers[task_id] = row_key
        self.runtimes[task_id] = time.time()

        # add periodic update of runtimes
        if not self.update_timer:
            self.update_timer = self.set_interval(3.0, self.update_runtimes)

    def update_runtimes(self) -> None:
        time_now = time.time()
        has_active_tasks = False
        for worker_name, row_key in self.row_key_workers.items():
            # Only update if the task is active
            if self.get_cell(row_key, "status") == "active":
                has_active_tasks = True
                start_time = self.runtimes.get(worker_name)
                if start_time:
                    runtime = time_now - start_time
                    minutes = int(runtime // 60)
                    seconds = int(runtime % 60)
                    self.update_cell(row_key, "runtime", f"{minutes:02d}:{seconds:02d}")

        # stop the update timer if there are no active tasks
        if not has_active_tasks and self.update_timer:
            self.update_timer.stop()
            self.update_timer = None

    def should_track(self, command: str) -> bool:
        if command.startswith("/"):
            cmd = command[1:]
            return cmd in self.tracked_commands
        # if it doesn't start with / then it's a chat, so track
        return True

    def worker_updated(self, worker: Worker, state: WorkerState) -> None:
        if state == WorkerState.SUCCESS:
            row_key = self.row_key_workers.get(worker.name)
            if row_key is not None:
                self.update_cell(row_key, "status", "done")  # 4 = index of "status" column

    def set_task_finished(self, task_id):
        row_key = self.row_key_workers.get(task_id)
        if row_key is not None:
            self.update_cell(row_key, "status", "done")

    def update_input_tokens(self, worker_id, token_count, model=None):
        row_key = self.row_key_workers.get(worker_id)
        if row_key is not None:
            self.update_cell(row_key, "tok_in", token_count)
            if model:
                self.update_cell(row_key, "model", model)

    def update_output_tokens(self, worker_id, token_count, tokens_per_second):
        row_key = self.row_key_workers.get(worker_id)
        if row_key is not None:
            self.update_cell(row_key, "tok_out", token_count)
            self.update_cell(row_key, "tok/sec", tokens_per_second)