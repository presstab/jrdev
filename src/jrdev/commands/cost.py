from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, cast

from jrdev.core.usage import get_instance
from jrdev.models.model_utils import get_model_cost
from jrdev.ui.ui import PrintType


@dataclass
class CostInfo:
    """A structured way to hold cost, token, and provider information."""

    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost_dollars: float = 0.0
    output_cost_dollars: float = 0.0

    @property
    def total_cost_dollars(self) -> float:
        return self.input_cost_dollars + self.output_cost_dollars

    def __add__(self, other: "CostInfo") -> "CostInfo":
        """Allows adding two CostInfo objects for easy aggregation."""
        # The provider for a total sum is meaningless, so we can leave it blank.
        return CostInfo(
            provider="",
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            input_cost_dollars=self.input_cost_dollars + other.input_cost_dollars,
            output_cost_dollars=self.output_cost_dollars + other.output_cost_dollars,
        )


# pylint: disable=too-many-locals
def _process_usage_data(
    ui: Any,
    usage_data: Dict[str, Dict],
    models_by_name: Dict[str, Dict],
    available_models: List[Dict],  # Needed for get_model_cost
) -> Tuple[Dict[str, CostInfo], CostInfo]:
    """Processes raw usage data and calculates all costs.

    Returns:
        A tuple containing (costs_by_model, total_cost).
    """
    costs_by_model: Dict[str, CostInfo] = {}
    total_cost = CostInfo(provider="")  # Start with an empty total

    for model_name, tokens in usage_data.items():
        model_entry = models_by_name.get(model_name)
        if not model_entry:
            ui.print_text(f"Warning: No model entry found for model {model_name}", PrintType.WARNING)
            continue

        model_cost_data = cast(Dict[str, float], get_model_cost(model_name, available_models))
        if not model_cost_data:
            ui.print_text(f"Warning: No cost data available for model {model_name}", PrintType.WARNING)
            continue

        provider = model_entry.get("provider", "")
        input_tokens = tokens.get("input_tokens", 0)
        output_tokens = tokens.get("output_tokens", 0)

        # costs (per million tokens)
        input_cost = (input_tokens * model_cost_data["input_cost"]) / 1_000_000
        output_cost = (output_tokens * model_cost_data["output_cost"]) / 1_000_000

        # Create the structured cost object for this model
        model_cost_info = CostInfo(
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_dollars=input_cost,
            output_cost_dollars=output_cost,
        )

        costs_by_model[model_name] = model_cost_info
        total_cost += model_cost_info  # Aggregate totals

    return costs_by_model, total_cost


def _display_cost_report(ui: Any, costs_by_model: Dict[str, CostInfo], total_cost: CostInfo) -> None:
    """Displays the full cost report, including totals and per-model breakdown."""

    def _format_cost_line(label: str, cost_dollars: float) -> str:
        return f"{label}: ${cost_dollars:.4f}"

    def _print_summary_block(title: str, cost_info: CostInfo) -> None:
        ui.print_text(f"\n{title}", PrintType.HEADER)
        ui.print_text(f"Tokens used: {cost_info.input_tokens} input, {cost_info.output_tokens} output", PrintType.INFO)
        ui.print_text(
            _format_cost_line("Total cost", cost_info.total_cost_dollars),
            PrintType.INFO,
        )
        ui.print_text(
            _format_cost_line("Input cost", cost_info.input_cost_dollars),
            PrintType.INFO,
        )
        ui.print_text(
            _format_cost_line("Output cost", cost_info.output_cost_dollars),
            PrintType.INFO,
        )

    # Display total cost information
    _print_summary_block("=== TOTAL SESSION COST ===", total_cost)

    # Display cost breakdown by model
    ui.print_text("\n=== COST BREAKDOWN BY MODEL ===", PrintType.HEADER)
    for model_name, cost_info in costs_by_model.items():
        _print_summary_block(f"Model: {model_name}", cost_info)


async def handle_cost(app: Any, _cmd_parts: List[str], _worker_id: str) -> None:
    """
    Calculates and displays a report of token usage and estimated costs for the session.

    The report shows the total cost and a breakdown of input/output tokens and
    costs for each model used during the current application session.

    Usage:
      /cost
    """
    usage_data = await get_instance().get_usage()
    if not usage_data:
        app.ui.print_text("No usage data available. Try running some queries first.", PrintType.INFO)
        return

    available_models = app.state.model_list.get_model_list()
    models_by_name = {m["name"]: m for m in available_models}

    # 1. Process all data and calculate costs
    costs_by_model, total_cost = _process_usage_data(app.ui, usage_data, models_by_name, available_models)

    # 2. Display the final report
    _display_cost_report(app.ui, costs_by_model, total_cost)
