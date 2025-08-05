from typing import List, Dict, Any, Set
from enum import Enum
from textual.widgets import Button, DataTable
from textual.binding import Binding
from textual.widgets.data_table import RowKey, ColumnKey, Column
from textual import on
from datetime import datetime
from rich.text import Text

from jrdev.ui.tui.settings.model_management.base_model_modal import BaseModelModal
from jrdev.ui.tui.command_request import CommandRequest

import logging
logger = logging.getLogger("jrdev")


class SortingStatus(Enum):
    UNSORTED = 0
    ASCENDING = 1
    DESCENDING = 2


class ImportModelsModal(BaseModelModal):
    """A modal to import models from a provider."""

    DEFAULT_CSS = BaseModelModal.DEFAULT_CSS + """
    ImportModelsModal > .model-modal-container {
        border: round $accent;
        width: 80%;
        height: 80%;
    }
    #import-models-table {
        height: 1fr;
        border: round $accent;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Close", show=False),
    ]

    def __init__(self, models: List[Dict[str, Any]], provider_name: str, **kwargs):
        super().__init__(**kwargs)
        self.models_to_import = models
        self.provider_name = provider_name
        self.selected_rows: Set[RowKey] = set()
        self._row_key_to_model: Dict[RowKey, Dict[str, Any]] = {}
        # Sorting state per column (by ColumnKey.value)
        self._sorting_statuses: Dict[str, SortingStatus] = {
            "select": SortingStatus.UNSORTED,
            "name": SortingStatus.UNSORTED,
            "date": SortingStatus.UNSORTED,
            "context": SortingStatus.UNSORTED,
            "input": SortingStatus.UNSORTED,
            "output": SortingStatus.UNSORTED,
        }

    def compose(self):
        container, header = self.build_container("import-models-container", f"Import Models from {self.provider_name}")
        with container:
            yield header
            yield DataTable(id="import-models-table")

            # Build actions row using the base class helper to ensure consistent IDs
            actions = self.actions_row()
            yield actions

    def on_mount(self):
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        # Add columns with keys to support sorting and header label updates
        table.add_column("[yellow]-[/]", key="select")
        table.add_column("Name [yellow]-[/]", key="name")
        table.add_column("Date Added [yellow]-[/]", key="date")
        table.add_column("Context [yellow]-[/]", key="context")
        table.add_column("Input Cost/1M [yellow]-[/]", key="input")
        table.add_column("Output Cost/1M [yellow]-[/]", key="output")

        # Build a set of existing local model names (as stored in jrdev)
        existing_model_names = {str(model.get('name', '')).strip() for model in self.app.jrdev.get_models() if model.get('name')}

        for model in self.models_to_import:
            # Prefer a 'name' field if present; otherwise fall back to 'id'
            raw_name = model.get('name') or model.get('id')
            candidate_name = str(raw_name).strip() if raw_name else ""
            if not candidate_name:
                # If we cannot determine a comparable name, skip this entry
                continue
            # Only skip when the candidate name exactly matches an existing local model name
            if candidate_name in existing_model_names:
                continue

            # stored locally as cost per 10m tokens
            input_cost_per_1M = model.get("input_cost", 0) / 10
            output_cost_per_1M = model.get("output_cost", 0) / 10

            context_length = model.get('context_tokens', 0)

            # unix time that model was created
            created_time = model.get('created', 0)
            try:
                created_time_str = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d') if created_time else ""
            except Exception:
                created_time_str = ""

            input_cost_str = f"${input_cost_per_1M:.2f}"
            output_cost_str = f"${output_cost_per_1M:.2f}"

            row_key = table.add_row(
                "☐",
                candidate_name,
                created_time_str,
                str(context_length),
                input_cost_str,
                output_cost_str,
                key=candidate_name
            )
            self._row_key_to_model[row_key] = model

        # Initialize default sort on Date Added with newest first (descending by date)
        if table.columns:
            try:
                date_column = table.columns[ColumnKey("date")]
                # Reset headers, set date column to DESCENDING state visually and functionally
                self._reset_all_header_labels(table)
                # Sort by newest first
                self._sorting_statuses["date"] = SortingStatus.ASCENDING
                table.sort(date_column.key, reverse=True)
                date_column.label = Text.from_markup(f"{self._pretty_header_text('date')} [yellow]↑[/]")
            except Exception as e:
                logger.debug(f"Failed to set initial sort: {e}")

        # Update the save button label and disabled state after the DOM is ready
        save_button = self.query_one("#save", Button)
        save_button.label = "Import"
        save_button.disabled = not self.selected_rows

    def _reset_all_header_labels(self, table: DataTable) -> None:
        for key in list(self._sorting_statuses.keys()):
            # reset stored state
            self._sorting_statuses[key] = SortingStatus.UNSORTED
            # update visual label on column if it exists
            try:
                col_index = table.get_column_index(key)
                col = table.ordered_columns[col_index]
                base = self._pretty_header_text(key)
                col.label = Text.from_markup(f"{base} [yellow]-[/]")
            except Exception:
                continue

    def _pretty_header_text(self, key: str) -> str:
        mapping = {
            "select": "✓",
            "name": "Name",
            "date": "Date Added",
            "context": "Context",
            "input": "Input Cost/1M",
            "output": "Output Cost/1M",
        }
        return mapping.get(key, key)

    def _apply_sort_to_column(self, column: Column, column_key: ColumnKey, initial: bool = False) -> None:
        table = self.query_one(DataTable)
        key = column_key.value
        if key not in self._sorting_statuses:
            # do nothing for unknown keys
            return

        sort_key_func = None
        if key in ["context", "input", "output"]:
            def sort_key(value: Text) -> float:
                try:
                    # For cost columns, remove '$' and convert to float.
                    # For context, just convert to float/int.
                    return float(str(value).lstrip('$'))
                except (ValueError, TypeError):
                    return 0.0
            sort_key_func = sort_key

        # If UNSORTED or initial call, set to ASCENDING and reset others
        if initial or self._sorting_statuses[key] == SortingStatus.UNSORTED:
            self._reset_all_header_labels(table)
            self._sorting_statuses[key] = SortingStatus.ASCENDING
            # ASCENDING corresponds to reverse=True for Textual to show ↑ (per example)
            table.sort(column_key, reverse=True, key=sort_key_func)
            column.label = Text.from_markup(f"{self._pretty_header_text(key)} [yellow]↑[/]")
        elif self._sorting_statuses[key] == SortingStatus.ASCENDING:
            self._sorting_statuses[key] = SortingStatus.DESCENDING
            table.sort(column_key, reverse=False, key=sort_key_func)
            column.label = Text.from_markup(f"{self._pretty_header_text(key)} [yellow]↓[/]")
        elif self._sorting_statuses[key] == SortingStatus.DESCENDING:
            self._sorting_statuses[key] = SortingStatus.ASCENDING
            table.sort(column_key, reverse=True, key=sort_key_func)
            column.label = Text.from_markup(f"{self._pretty_header_text(key)} [yellow]↑[/]")

    @on(DataTable.HeaderSelected, "#import-models-table")
    def handle_header_selected(self, event: DataTable.HeaderSelected) -> None:
        table = self.query_one(DataTable)
        try:
            column = table.columns[event.column_key]
        except Exception:
            return
        # Do not sort on the checkbox column; allow toggling only by row select
        if event.column_key.value == "select":
            return
        self._apply_sort_to_column(column, column.key)

    @on(DataTable.RowSelected, "#import-models-table")
    def toggle_row_selection(self, event: DataTable.RowSelected):
        table = self.query_one(DataTable)
        row_key = event.row_key
        if not row_key:
            return
        check_col_key = table.ordered_columns[0].key
        if check_col_key is None:
            return
        if row_key in self.selected_rows:
            self.selected_rows.remove(row_key)
            table.update_cell(row_key, column_key=check_col_key, value="☐")
        else:
            self.selected_rows.add(row_key)
            table.update_cell(row_key, column_key=check_col_key, value="☑")
        
        # Update the disabled state of the Import button
        save_button = self.query_one("#save", Button)
        save_button.disabled = not self.selected_rows

        table.move_cursor(row=-1)

    @on(Button.Pressed, "#save")
    def handle_save_press(self, event: Button.Pressed):
        if not self.selected_rows:
            self.app.notify("No models selected for import.", severity="warning")
            return

        for row_key in self.selected_rows:
            model_data = self._row_key_to_model.get(row_key)
            if not model_data:
                continue

            # Use the same candidate name logic for consistency when issuing the add command
            name = (model_data.get('name') or model_data.get('id'))
            if not name:
                continue
            name = str(name).strip()

            provider = self.provider_name
            is_think = "true"

            input_cost_per_1M = float(model_data.get('input_cost', 0))
            output_cost_per_1M = float(model_data.get('output_cost', 0))

            #store internally as cost per 10m
            input_cost = 0 if not input_cost_per_1M else input_cost_per_1M / 10
            output_cost = 0 if not output_cost_per_1M else output_cost_per_1M / 10

            context_window = model_data.get('context_tokens', 0)

            command = f"/model add {name} {provider} {is_think} {input_cost:.6f} {output_cost:.6f} {context_window}"
            logger.info(f"importing model {command}")
            self.post_message(CommandRequest(command))

        self.app.pop_screen()
        self.app.notify(f"Importing {len(self.selected_rows)} models...")


    @on(Button.Pressed, "#cancel")
    def handle_cancel_press(self):
        self.app.pop_screen()
