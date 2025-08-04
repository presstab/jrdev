from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Select
from textual.containers import Vertical, Horizontal
from jrdev.utils.string_utils import is_valid_name, is_valid_cost, is_valid_context_window


def _parse_bool(val: str) -> bool:
    true_vals = {"1", "true", "yes", "y", "on"}
    false_vals = {"0", "false", "no", "n", "off"}
    if val.lower() in true_vals:
        return True
    if val.lower() in false_vals:
        return False
    raise ValueError(f"Invalid boolean value: {val}")


class BaseModelModal(ModalScreen):
    """Shared base modal for AddModelModal and EditModelModal.

    Centralizes common styling, layout helpers, and validation/transform helpers
    to keep the two modals visually and behaviorally consistent.
    """

    DEFAULT_CSS = """
    BaseModelModal {
        align: center middle;
        background: transparent;
    }

    /* Shared container defaults; allow id-specific overrides in subclasses */
    .model-modal-container {
        width: 50%;
        min-width: 24;
        height: auto;
        padding: 1;
        margin: 0;
        align: center middle;
        border: round $accent;
        background: #1e1e1e 80%;
        overflow: hidden;
        content-align: center middle;
    }

    .model-modal-container > Label {
        padding: 0;
        margin: 0 0 1 0;
    }

    /* Form row styling */
    .form-row {
        layout: horizontal;
        width: 100%;
        height: 3;
        align-vertical: bottom;
        padding: 0 0 0 1;
        background: #1e1e1e 80%;
    }

    .form-row > .form-label {
        width: 20;
        min-width: 16;
        text-align: left;
        color: $text;
    }

    .form-row > Input {
        width: 1fr;
        height: 3;
        border: round $accent;
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
            border: tall $border-blurred;
            background: $surface;
            &:focus {
                background-tint: $foreground 5%;
            }
            & > .option-list--option {
                padding: 0 1;
            }
        }
        &.-expanded {
            .down-arrow { display: none; }
            .up-arrow { display: block; }
            & > SelectOverlay { display: block; }
        }
    }

    /* Action buttons row */
    .form-actions {
        layout: horizontal;
        width: 100%;
        height: auto;
        align: left middle;
        padding-top: 1;
        padding-left: 1;
    }

    .form-actions > Button#save,
    .form-actions > Button#cancel {
        width: 1fr;
        max-width: 10;
        height: 1;
        margin-left: 1;
    }
    """

    # -----------------------------
    # Shared helpers
    # -----------------------------

    def build_container(self, container_id: str, title: str) -> tuple[Vertical, Label]:
        """Create a standard modal container with a header label.

        Subclasses should use this to ensure consistent structure.
        """
        container = Vertical(id=container_id, classes="model-modal-container")
        header = Label(title)
        return container, header

    def labeled_row(self, label_text: str, widget) -> Horizontal:
        """Return a Horizontal row with a left label and a right field widget."""
        return Horizontal(
            Label(label_text, classes="form-label"),
            widget,
            classes="form-row"
        )

    def actions_row(self) -> Horizontal:
        """Return a row with Save and Cancel buttons, ensuring standard IDs."""
        save_button = Button("Save", id="save")
        cancel_button = Button("Cancel", id="cancel")
        return Horizontal(
            save_button,
            cancel_button,
            classes="form-actions"
        )

    # -----------------------------
    # Validation and conversion helpers
    # -----------------------------

    def parse_bool(self, value: str) -> bool:
        return _parse_bool(value)

    def validate_name(self, name: str) -> bool:
        return is_valid_name(name)

    def parse_cost_display(self, value: str, field_name: str) -> float | None:
        """Parse a per-1M tokens cost from string; notifies on error and returns None."""
        try:
            cost = float(value)
        except (TypeError, ValueError):
            self.app.notify(f"Invalid {field_name} (per 1M tokens)", severity="error")
            return None
        if not is_valid_cost(cost):
            self.app.notify(f"Invalid {field_name} (per 1M tokens)", severity="error")
            return None
        return cost

    def display_to_stored_cost(self, per_1m: float) -> float:
        """Convert display units (per 1M tokens) to stored units (per 10M tokens)."""
        return per_1m * 10.0

    def stored_to_display_cost(self, per_10m: float | int | str) -> float:
        """Convert stored units (per 10M tokens) to display units (per 1M tokens)."""
        try:
            val = float(per_10m)
        except (TypeError, ValueError):
            val = 0.0
        return val / 10.0

    def parse_context_window(self, value: str) -> int | None:
        try:
            ctx = int(value)
        except (TypeError, ValueError):
            self.app.notify("Invalid context window", severity="error")
            return None
        if not is_valid_context_window(ctx):
            self.app.notify("Invalid context window", severity="error")
            return None
        return ctx

    # -----------------------------
    # Shared population helpers
    # -----------------------------

    def populate_providers(self, select: Select) -> None:
        providers = self.app.jrdev.provider_list()
        provider_options = [(provider.name, provider.name) for provider in providers]
        select.set_options(provider_options)
