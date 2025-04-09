from textual.widgets import DataTable, Label
from textual.color import Color
from textual.worker import Worker, WorkerState
import logging
import time
logger = logging.getLogger("jrdev")


class TaskMonitor(DataTable):

    def __init__(self):
        super().__init__()
        self.column_names = ["id", "task", "model", "input_tokens", "output_tokens", "tokens/sec", "runtime", "status"]
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
            self.add_column(column, key=column)

    def add_task(self, worker: Worker, task_id: str, task_name: str, model: str) -> None:
        if not task_name.startswith("/"):
            task_name = "chat"
        row = (task_id, task_name, model, 0, 0, 0, 0, "active")
        row_key = self.add_row(*row, key=task_id)
        self.row_key_workers[worker.name] = row_key
        logger.info(f"add_task worker_name: {worker.name}")
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
            return command in self.tracked_commands
        # if it doesn't start with / then it's a chat, so track
        return True

    def worker_updated(self, worker: Worker, state: WorkerState) -> None:
        if state == WorkerState.SUCCESS:
            row_key = self.row_key_workers.get(worker.name)
            if row_key is not None:
                self.update_cell(row_key, "status", "done")  # 4 = index of "status" column

    def update_input_tokens(self, worker_id, token_count, model=None):
        row_key = self.row_key_workers.get(worker_id)
        if row_key is not None:
            self.update_cell(row_key, "input_tokens", token_count)
            if model:
                self.update_cell(row_key, "model", model)

    def update_output_tokens(self, worker_id, token_count, tokens_per_second):
        row_key = self.row_key_workers.get(worker_id)
        if row_key is not None:
            self.update_cell(row_key, "output_tokens", token_count)
            self.update_cell(row_key, "tokens/sec", tokens_per_second)