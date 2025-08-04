from typing import List, Dict, Any, Set
from textual.widgets import Button, DataTable
from textual.binding import Binding
from textual.widgets.data_table import RowKey
from textual import on
from datetime import datetime

from jrdev.ui.tui.base_model_modal import BaseModelModal
from jrdev.ui.tui.command_request import CommandRequest

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

    def compose(self):
        container, header = self.build_container("import-models-container", f"Import Models from {self.provider_name}")
        with container:
            yield header
            yield DataTable(id="import-models-table")

            # Build actions row using the base class helper to ensure consistent IDs
            actions = self.actions_row()
            # Access the known save button (id="save") and adjust its label
            for child in actions.children:
                if isinstance(child, Button) and child.id == "save":
                    child.label = "Import"
                    break
            yield actions

    def on_mount(self):
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("✓", "Name", "Date Added", "Context", "Input Cost/1M", "Output Cost/1M")
        
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
            created_time_str = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d')
            
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
        
        table.move_cursor(row=-1)

    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed):
        if event.button.id == "save":
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
                
                input_cost_per_token = float(model_data.get('pricing', {}).get('input', '0'))
                output_cost_per_token = float(model_data.get('pricing', {}).get('output', '0'))
            
                input_cost_per_1M = input_cost_per_token * 1_000_000
                output_cost_per_1M = output_cost_per_token * 1_000_000

                context_window = model_data.get('context_length', 0)

                command = f"/model add {name} {provider} {is_think} {input_cost_per_1M:.6f} {output_cost_per_1M:.6f} {context_window}"
                self.post_message(CommandRequest(command))
            
            self.app.pop_screen()
            self.app.notify(f"Importing {len(self.selected_rows)} models...")
        elif event.button.id == "cancel":
            self.app.pop_screen()
