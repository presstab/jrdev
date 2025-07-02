from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Button
from textual.color import Color
from textual.worker import Worker, WorkerState
from jrdev.ui.textual_events import TextualEvents
import logging
import time

from jrdev.models.model_utils import get_model_cost, Price_Per_Token_Scale

logger = logging.getLogger("jrdev")


class TaskMonitorTable(DataTable):
    BINDINGS = [
        ("up", "cursor_up", "Cursor Up"),
        ("down", "cursor_down", "Cursor Down"),
    ]

    def __init__(self, jrdev_app, id: Optional[str] = None):
        super().__init__(id=id)
        self.jrdev = jrdev_app
        self.column_names = ["id", "task", "model", "tok_in", "tok_out", "tok/sec", "cost", "runtime", "status"]
        self.row_key_workers = {}  # {row_key: worker.name}
        self.runtimes = {}  # {worker.name: start_time}
        self.update_timer = None
        self.tracked_commands = [
            "init",
            "code",
            "chat",
            "asyncsend",
            "git pr review",
            "git pr summary"
        ]
        # --- Subtask tracking ---
        # Maps subtask_id -> main_task_id
        self.subtask_to_main = {}
        # Maps main_task_id -> set of subtask_ids
        self.main_to_subtasks = {}

    async def on_mount(self) -> None:
        # Apply scrollbar styling directly or via CSS if preferred
        self.styles.scrollbar_background = "#1e1e1e"
        self.styles.scrollbar_background_hover = "#1e1e1e"
        self.styles.scrollbar_background_active = "#1e1e1e"
        self.styles.scrollbar_color = "#63f554 30%"
        self.styles.scrollbar_color_active = "#63f554"
        self.styles.scrollbar_color_hover = "#63f554 50%"
        for column in self.column_names:
            if column == "model":
                self.add_column(column, key=column, width=16)
            else:
                self.add_column(column, key=column)

    def truncate_cell_content(self, content: str, max_width: int) -> str:
        return content if len(content) <= max_width else content[:max_width - 1] + "…"

    def add_task(self, task_id: str, task_name: str, model: str, sub_task_name: Optional[str] = None, parent_task_id: Optional[str] = None) -> None:
        if not sub_task_name and not task_name.startswith("/"):
            task_name = "chat"
        use_name = task_name
        if sub_task_name:
            use_name = sub_task_name
        use_name = self.truncate_cell_content(use_name, 20)
        row = (task_id, use_name, model, 0, 0, 0, "$0.00", 0, "active")
        row_key = self.add_row(*row, key=task_id)
        self.row_key_workers[task_id] = row_key
        self.runtimes[task_id] = time.time()

        # --- Subtask tracking logic ---
        if parent_task_id:
            self.subtask_to_main[task_id] = parent_task_id
            if parent_task_id not in self.main_to_subtasks:
                self.main_to_subtasks[parent_task_id] = set()
            self.main_to_subtasks[parent_task_id].add(task_id)
        else:
            # If this is a main task, ensure it has an entry in main_to_subtasks
            if task_id not in self.main_to_subtasks:
                self.main_to_subtasks[task_id] = set()

        # add periodic update of runtimes
        if not self.update_timer:
            self.update_timer = self.set_interval(3.0, self.update_runtimes)

    def has_active_tasks(self) -> bool:
        for worker_name, row_key in self.row_key_workers.items():
            # Only update if the task is active
            if self.get_cell(row_key, "status") == "active":
                return True
        return False

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
            if "git pr review" in command or "git pr summary" in command:
                return True
            # remove the / and only include first word
            cmd = command[1:].split(" ")[0]
            return cmd in self.tracked_commands
        # if it doesn't start with / then it's a chat, so track
        return True

    def worker_updated(self, worker: Worker, state: WorkerState) -> None:
        row_key = self.row_key_workers.get(worker.name)
        if row_key is not None:
            if state == WorkerState.SUCCESS:
                self.update_cell(row_key, "status", "done")
            elif state == WorkerState.CANCELLED:
                self.update_cell(row_key, "status", "cancelled")
                # --- Cancel all subtasks if this is a main task ---
                subtasks = self.main_to_subtasks.get(worker.name, set())
                for subtask_id in subtasks:
                    sub_row_key = self.row_key_workers.get(subtask_id)
                    if sub_row_key is not None:
                        self.update_cell(sub_row_key, "status", "cancelled")
            elif state == WorkerState.ERROR:
                self.update_cell(row_key, "status", "error")

    def set_task_finished(self, task_id):
        row_key = self.row_key_workers.get(task_id)
        if row_key is not None:
            self.update_cell(row_key, "status", "done")

    def _get_task_cost(self, row_key) -> float:
        try:
            model_name = self.get_cell(row_key, "model")
            if not model_name:
                return 0.0

            costs = get_model_cost(model_name, self.jrdev.get_models())
            if not costs:
                return 0.0

            input_tokens = int(self.get_cell(row_key, "tok_in"))
            output_tokens = int(self.get_cell(row_key, "tok_out"))

            # Costs are per million tokens
            input_cost_per_mil = float(costs.get("input_cost", 0))
            output_cost_per_mil = float(costs.get("output_cost", 0))

            return (input_tokens * input_cost_per_mil / 1_000_000) + (output_tokens * output_cost_per_mil / 1_000_000)
        except (ValueError, TypeError):  # Can happen if cells are not numbers yet
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating cost for row {row_key}: {e}")
            return 0.0

    def _recalculate_and_update_cost(self, row_key) -> None:
        try:
            task_id = self.get_cell(row_key, "id")

            # Update the individual task's cost first. This is for sub-tasks to show their own cost.
            # For main tasks, this will be overwritten by the aggregate cost later if it has subtasks.
            task_cost = self._get_task_cost(row_key)
            self.update_cell(row_key, "cost", f"${task_cost:.4f}")

            # Determine which main task needs its aggregate cost recalculated.
            # If task_id is a subtask, it's the parent. Otherwise, it's task_id itself.
            main_task_id_to_update = self.subtask_to_main.get(task_id, task_id)

            # Only proceed if it's a known main task (i.e., it can have subtasks).
            if main_task_id_to_update in self.main_to_subtasks:
                main_task_row_key = self.row_key_workers.get(main_task_id_to_update)
                if main_task_row_key:
                    # Aggregate cost: main task's own cost + sum of all its subtasks' costs.
                    total_cost = self._get_task_cost(main_task_row_key)

                    subtask_ids = self.main_to_subtasks.get(main_task_id_to_update, set())
                    for sub_id in subtask_ids:
                        sub_row_key = self.row_key_workers.get(sub_id)
                        if sub_row_key:
                            total_cost += self._get_task_cost(sub_row_key)

                    self.update_cell(main_task_row_key, "cost", f"${total_cost:.4f}")
        except Exception as e:
            logger.error(f"Error calculating cost for row {row_key}: {e}")

    def update_input_tokens(self, worker_id, token_count, model=None):
        row_key = self.row_key_workers.get(worker_id)
        if row_key is not None:
            self.update_cell(row_key, "tok_in", token_count)
            if model:
                self.update_cell(row_key, "model", model)
            self._recalculate_and_update_cost(row_key)

    def update_output_tokens(self, worker_id, token_count, tokens_per_second):
        row_key = self.row_key_workers.get(worker_id)
        if row_key is not None:
            self.update_cell(row_key, "tok_out", token_count)
            self.update_cell(row_key, "tok/sec", tokens_per_second)
            self._recalculate_and_update_cost(row_key)


class TaskMonitor(Vertical):
    DEFAULT_CSS = """
    TaskMonitor {
        layout: vertical;
    }
    #task_monitor_table {
        height: 1fr;
        border: none;
        scrollbar-size: 1 1;
    }
    #stop-button {
        height: 1;
        dock: bottom;
        width: auto;
        align-horizontal: left;
    }
    """

    def __init__(self, jrdev_app, id: Optional[str] = None):
        super().__init__(id=id)
        self._table = TaskMonitorTable(jrdev_app=jrdev_app, id="task_monitor_table")
        self.button_stop = Button("Stop Tasks", id="stop-button")

    def compose(self) -> ComposeResult:
        yield self._table
        yield self.button_stop

    async def on_mount(self) -> None:
        # Apply border styling to the container
        self.border_title = "Tasks"
        self.styles.border = ("round", Color.parse("#5e5e5e"))
        self.styles.border_title_color = "#fabd2f"
        self._table.can_focus = False
        self.button_stop.disabled = True

    def update_stop_button_state(self) -> None:
        # Stop Tasks is disabled unless there are tasks actively running
        self.button_stop.disabled = not self._table.has_active_tasks()

    def handle_task_update(self, message: TextualEvents.TaskUpdate) -> None:
        if "input_token_estimate" in message.update:
            # first message gives us input token estimate and model being used
            token_count = message.update["input_token_estimate"]
            model = message.update["model"]
            self.update_input_tokens(message.worker_id, token_count, model)
        elif "output_token_estimate" in message.update:
            token_count = message.update['output_token_estimate']
            tokens_per_second = message.update["tokens_per_second"]
            self.update_output_tokens(message.worker_id, token_count, tokens_per_second)
        elif "input_tokens" in message.update:
            # final official accounting of tokens
            input_tokens = message.update.get("input_tokens")
            self.update_input_tokens(message.worker_id, input_tokens)
            output_tokens = message.update.get("output_tokens")
            tokens_per_second = message.update.get("tokens_per_second")
            self.update_output_tokens(message.worker_id, output_tokens, tokens_per_second)
        elif "new_sub_task" in message.update:
            # new sub task spawned
            sub_task_id = message.update.get("new_sub_task")
            description = message.update.get("description")
            parent_task_id = message.worker_id
            self.add_task(sub_task_id, task_name="init", model="", sub_task_name=description, parent_task_id=parent_task_id)
        elif "sub_task_finished" in message.update:
            self.set_task_finished(message.worker_id)

    # --- Delegate methods to the internal table --- #

    def add_task(self, *args, **kwargs):
        self._table.add_task(*args, **kwargs)
        self.update_stop_button_state()

    def worker_updated(self, *args, **kwargs):
        self._table.worker_updated(*args, **kwargs)
        self.update_stop_button_state()

    def set_task_finished(self, *args, **kwargs):
        self._table.set_task_finished(*args, **kwargs)
        self.update_stop_button_state()

    def update_input_tokens(self, *args, **kwargs):
        self._table.update_input_tokens(*args, **kwargs)

    def update_output_tokens(self, *args, **kwargs):
        self._table.update_output_tokens(*args, **kwargs)

    def should_track(self, *args, **kwargs) -> bool:
        return self._table.should_track(*args, **kwargs)
