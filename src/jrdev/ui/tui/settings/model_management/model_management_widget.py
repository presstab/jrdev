from typing import Any, Optional
from textual import on
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Select, Button, Label
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widget import Widget
from jrdev.ui.tui.settings.model_management.add_model_modal import AddModelModal
from jrdev.ui.tui.settings.model_management.add_provider_modal import AddProviderModal
from jrdev.ui.tui.settings.model_management.edit_provider_modal import EditProviderModal
from jrdev.ui.tui.settings.model_management.edit_model_modal import EditModelModal
from jrdev.ui.tui.settings.model_management.remove_model_modal import RemoveResourceModal
from jrdev.ui.tui.settings.model_management.import_models_modal import ImportModelsModal
from enum import Enum
from rich.text import Text

import logging
logger = logging.getLogger("jrdev")


class SortingStatus(Enum):
    UNSORTED = 0
    ASCENDING = 1
    DESCENDING = 2


class ModelManagementWidget(Widget):
    """A widget to manage models and providers."""

    DEFAULT_CSS = """
    ModelManagementWidget {
        layout: horizontal;
    }

    #left-pane {
        width: 3fr;
        max-width: 25;
        padding: 1;
        border-right: solid $primary;
    }

    #right-pane {
        width: 7fr;
        padding: 1;
        overflow-x: auto;
    }
    
    #models-scroll {
        height: 1fr;
        width: 100%;
        overflow-x: auto;
        overflow-y: auto;
    }

    #models-table {
        width: auto;
        min-width: 100%;
        overflow-x: auto;
    }
    
    #models-crud-bar {
        width: 100%;
        padding-top: 1;
        height: auto;
    }
    
    #provider-buttons-layout {
        height: 1;
        margin: 0;
        padding: 0;
    }
    
    .provider-button {
        margin-left: 1;
        width: 6;
        max-width: 6;
    }
    .provider-button-add-remove {
        margin-left: 1;
        width: 2;
        max-width: 3;
    }
    #provider-fetch {
        margin-top: 1;
    }
    .model-button {
        margin-left: 1;
        width: 6;
        max-width: 6;
    }
    .model-button-add-remove {
        margin-left: 1;
        width: 2;
        max-width: 3;
    }

    #models-table, #provider-select > SelectOverlay, #models-scroll {
        scrollbar-background: #1e1e1e;
        scrollbar-background-hover: #1e1e1e;
        scrollbar-background-active: #1e1e1e;
        scrollbar-color: #63f554 30%;
        scrollbar-color-active: #63f554;
        scrollbar-color-hover: #63f554 50%;
        scrollbar-size: 1 1;
        scrollbar-size-horizontal: 1;
    }

    #provider-select {
        height: 3;
        width: 1fr;
        max-width: 80;
        border: round $accent;
        margin: 0;
        padding: 0;
        & > SelectCurrent {
            border: none;
            background-tint: $foreground 5%;
        }
        & > SelectOverlay {
            width: 1fr;
            display: none;
            height: auto;
            max-height: 12;
            overlay: screen;
            constrain: none inside;
            color: $foreground;
            border: none;
            padding: 0;
            margin: 0;
            background: $surface;
            &:focus {
                background-tint: $foreground 5%;
            }
            & > .option-list--option {
                padding: 0;
            }
        }
        &.-expanded {
            .down-arrow { display: none; }
            .up-arrow { display: block; }
            & > SelectOverlay { display: block; }
        }
    }
    """

    def __init__(self, core_app: Any, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.core_app = core_app
        # map row keys to model names for selection-aware actions
        self._row_to_model: dict[Any, str] = {}
        # Sorting state for models table (by column key value)
        self._models_sorting_statuses: dict[str, SortingStatus] = {
            "name": SortingStatus.UNSORTED,
            "provider": SortingStatus.UNSORTED,
            "think": SortingStatus.UNSORTED,
            "input": SortingStatus.UNSORTED,
            "output": SortingStatus.UNSORTED,
            "context": SortingStatus.UNSORTED,
        }

    def compose(self):
        """Compose the widget."""
        with Horizontal():
            with Vertical(id="left-pane"):
                yield Label("Providers")
                yield Select([], id="provider-select")
                with Horizontal(id="provider-buttons-layout"):
                    yield Button("+", id="add-provider", classes="provider-button-add-remove", tooltip="Add new provider")
                    yield Button("-", id="remove-provider", classes="provider-button-add-remove", tooltip="Remove selected provider")
                    yield Button("Edit", id="edit-provider", classes="provider-button", tooltip="Edit selected provider")
                yield Button("Fetch Models", id="provider-fetch", tooltip="Fetch the updated list of models for the selected provider")
            with Container(id="right-pane"):
                yield Label("Models")
                with ScrollableContainer(id="models-scroll"):
                    yield DataTable(id="models-table")
                with Horizontal(id="models-crud-bar"):
                    yield Button("+", id="add-model", classes="model-button-add-remove", tooltip="Add new model")
                    yield Button("-", id="remove-model", classes="model-button-add-remove", disabled=True, tooltip="Remove selected model")
                    yield Button("Edit", id="edit-model", classes="model-button", disabled=True, tooltip="Edit selected model")

    def on_mount(self):
        """Populate the widgets with data."""
        self.populate_providers()
        self.populate_models()
        # initialize CRUD buttons state
        self._update_model_crud_buttons_state(False)
        # Disable Fetch Models button until a provider is selected
        fetch_button = self.query_one("#provider-fetch", Button)
        fetch_button.disabled = True

    def populate_providers(self):
        """Populates the provider select widget."""
        provider_select = self.query_one("#provider-select", Select)
        providers = self.core_app.provider_list()
        provider_options = [("ALL", "all")] + [(provider.name, provider.name) for provider in providers]
        provider_select.set_options(provider_options)

    def _models_pretty_header_text(self, key: str) -> str:
        mapping = {
            "name": "Name",
            "provider": "Provider",
            "think": "Think",
            "input": "Input Cost",
            "output": "Output Cost",
            "context": "Context",
        }
        return mapping.get(key, key)

    def _reset_models_header_labels(self, table: DataTable) -> None:
        for key in list(self._models_sorting_statuses.keys()):
            self._models_sorting_statuses[key] = SortingStatus.UNSORTED
            try:
                col_index = table.get_column_index(key)
                col = table.ordered_columns[col_index]
                base = self._models_pretty_header_text(key)
                col.label = Text.from_markup(f"{base} [yellow]-[/]")
            except Exception:
                continue

    def _apply_models_sort(self, column_key_value: str) -> None:
        table = self.query_one("#models-table", DataTable)
        try:
            column = table.columns[column_key_value]
        except Exception:
            return

        key = column.key.value
        if key not in self._models_sorting_statuses:
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

        if self._models_sorting_statuses[key] == SortingStatus.UNSORTED:
            self._reset_models_header_labels(table)
            self._models_sorting_statuses[key] = SortingStatus.ASCENDING
            table.sort(column.key, reverse=True, key=sort_key_func)
            column.label = Text.from_markup(f"{self._models_pretty_header_text(key)} [yellow]↑[/]")
        elif self._models_sorting_statuses[key] == SortingStatus.ASCENDING:
            self._models_sorting_statuses[key] = SortingStatus.DESCENDING
            table.sort(column.key, reverse=False, key=sort_key_func)
            column.label = Text.from_markup(f"{self._models_pretty_header_text(key)} [yellow]↓[/]")
        elif self._models_sorting_statuses[key] == SortingStatus.DESCENDING:
            self._models_sorting_statuses[key] = SortingStatus.ASCENDING
            table.sort(column.key, reverse=True, key=sort_key_func)
            column.label = Text.from_markup(f"{self._models_pretty_header_text(key)} [yellow]↑[/]")

    def populate_models(self, provider_filter: Optional[str] = None):
        """Populates the models table."""
        models_table = self.query_one("#models-table", DataTable)
        # Clear rows and columns to reset the table state safely
        models_table.clear(columns=True)
        self._row_to_model.clear()
        models_table.cursor_type = "row"
        # Prevent table from forcing full width expansion; allow content size and horizontal scroll
        models_table.styles.width = "auto"
        models_table.styles.min_width = "100%"
        models_table.styles.overflow_x = "auto"
        models_table.styles.overflow_y = "auto"
        models_table.fixed_columns = 0
        models_table.zebra_stripes = True

        # add columns with keys and neutral sort indicator in labels
        models_table.add_column("Name [yellow]-[/]", key="name")
        models_table.add_column("Provider [yellow]-[/]", key="provider")
        models_table.add_column("Think [yellow]-[/]", key="think")
        models_table.add_column("Input Cost [yellow]-[/]", key="input")
        models_table.add_column("Output Cost [yellow]-[/]", key="output")
        models_table.add_column("Context [yellow]-[/]", key="context")

        models = self.core_app.get_models()
        for model in models:
            if provider_filter and provider_filter != "all" and model["provider"] != provider_filter:
                continue

            # Stored costs are per 10M tokens; convert to display per 1M tokens by dividing by 10
            try:
                input_cost_stored = float(model.get("input_cost", 0))
            except (TypeError, ValueError):
                input_cost_stored = 0.0
            try:
                output_cost_stored = float(model.get("output_cost", 0))
            except (TypeError, ValueError):
                output_cost_stored = 0.0

            input_cost_display = input_cost_stored / 10.0
            output_cost_display = output_cost_stored / 10.0

            # Format to a sensible precision to avoid confusion
            input_cost_str = f"${input_cost_display:.2f}"
            output_cost_str = f"${output_cost_display:.2f}"

            row_key = models_table.add_row(
                model["name"],
                model["provider"],
                str(model.get("is_think", False)),
                input_cost_str,
                output_cost_str,
                str(model.get("context_tokens", 0)),
            )
            self._row_to_model[row_key] = model["name"]

        # Reset headers to neutral state after repopulating
        self._reset_models_header_labels(models_table)

        # after repopulating, ensure CRUD buttons reflect current selection
        self._update_model_crud_buttons_state(False)

    def _get_selected_model_name(self) -> Optional[str]:
        models_table = self.query_one("#models-table", DataTable)
        if not models_table.row_count:
            return None
        if models_table.cursor_row is None:
            return None
        try:
            row = models_table.cursor_row
            column = models_table.cursor_column
            cell_key = models_table.coordinate_to_cell_key(Coordinate(row, column))
        except Exception as e:
            logger.info("_get_selected_model_name(): Failed to get row key. Error: %s", e)
            return None
        return self._row_to_model.get(cell_key.row_key, None)

    def _update_model_crud_buttons_state(self, selected: bool) -> None:
        """Enable/disable Edit and Remove model buttons based on selection."""
        edit_btn = self.query_one("#edit-model", Button)
        remove_btn = self.query_one("#remove-model", Button)
        edit_btn.disabled = not selected
        remove_btn.disabled = not selected

    def sanitize_id(self, name: str) -> str:
        """Sanitizes a string to be used as a widget ID."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    @on(Select.Changed, "#provider-select")
    def handle_provider_change(self, event: Select.Changed):
        """Handle provider selection changes."""
        provider_select = self.query_one("#provider-select", Select)
        fetch_button = self.query_one("#provider-fetch", Button)
        selected = provider_select.value
        fetch_button.disabled = (not selected or selected == "all" or selected == Select.BLANK)
        self.populate_models(event.value)

    @on(DataTable.HeaderSelected, "#models-table")
    def handle_models_header_selected(self, event: DataTable.HeaderSelected) -> None:
        # All columns are sortable for this table
        if not event.column_key:
            return
        self._apply_models_sort(event.column_key.value)

    @on(DataTable.RowHighlighted, "#models-table")
    @on(DataTable.RowSelected, "#models-table")
    def handle_models_table_selection_changed(self, event: DataTable.RowHighlighted) -> None:
        """Toggle button enable state when table selection changes."""
        self._update_model_crud_buttons_state(event.row_key is not None)

    @on(Button.Pressed, "#add-provider")
    def add_provider(self):
        """Add a new provider."""
        self.app.push_screen(AddProviderModal())

    @on(Button.Pressed, "#edit-provider")
    def edit_provider(self):
        """Edit the selected provider."""
        provider_select = self.query_one("#provider-select", Select)
        provider_name = provider_select.value
        if provider_name and provider_name != "all":
            self.app.push_screen(EditProviderModal(provider_name))

    @on(Button.Pressed, "#remove-provider")
    def remove_provider(self):
        """Remove the selected provider."""
        provider_select = self.query_one("#provider-select", Select)
        provider_name = provider_select.value
        if provider_name is None or provider_name == "all" or provider_name == Select.BLANK:
            return
        self.app.push_screen(RemoveResourceModal(provider_name, resource_type="provider"))

    @on(Button.Pressed, "#add-model")
    def add_model(self):
        """Add a new model."""
        self.app.push_screen(AddModelModal())

    @on(Button.Pressed, "#edit-model")
    def edit_model(self):
        """Edit the selected model from the table."""
        model_name = self._get_selected_model_name()
        if model_name:
            self.app.push_screen(EditModelModal(model_name))

    @on(Button.Pressed, "#remove-model")
    def remove_model(self):
        """Remove the selected model from the table."""
        model_name = self._get_selected_model_name()
        if model_name:
            self.app.push_screen(RemoveResourceModal(model_name))

    @on(Button.Pressed, "#provider-fetch")
    async def fetch_provider_models(self):
        provider_select = self.query_one("#provider-select", Select)
        provider_name = provider_select.value

        if not provider_name or provider_name == "all" or provider_name == Select.BLANK:
            self.app.notify("Please select a specific provider to fetch models from.", severity="warning")
            return

        fetch_button = self.query_one("#provider-fetch", Button)
        try:
            fetch_button.disabled = True
            self.app.notify(f"Fetching models for {provider_name}...")
            models = await self.core_app.model_fetch_service.fetch_provider_models(provider_name, self.app.jrdev)

            if models:
                await self.app.push_screen(ImportModelsModal(models=models, provider_name=provider_name))
            else:
                self.app.notify(f"Could not fetch models for '{provider_name}'. The provider may not be supported for automatic fetching.", severity="error")
        except Exception as e:
            logger.error(f"Failed to fetch provider models: {e}")
            self.app.notify(f"An error occurred while fetching models: {e}", severity="error")
        finally:
            fetch_button.disabled = False
