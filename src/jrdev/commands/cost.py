"""Command implementation for cost tracking."""
from typing import List, Dict, Any, cast

from jrdev.model_utils import get_model_cost, VCU_Value
from jrdev.ui.ui import PrintType
from jrdev.usage import get_instance


def handle_cost_format_cost_line(label: str, dollar: float, vcu: float, show_vcu: bool) -> str:
    if show_vcu:
        return f"{label}: ${dollar:.4f} ({vcu:.4f} VCU)"
    else:
        return f"{label}: ${dollar:.4f}"

async def handle_cost(app: Any, cmd_parts: List[str], worker_id: str) -> None:
    """Handle the /cost command.

    Args:
        app: The Application instance
        cmd_parts: The command and its arguments
    """
    usage_tracker = get_instance()
    usage_data = await usage_tracker.get_usage()

    if not usage_data:
        app.ui.print_text("No usage data available. Try running some queries first.", PrintType.INFO)
        return

    # Calculate costs
    total_input_tokens = 0
    total_output_tokens = 0
    total_input_cost_vcu = 0.0
    total_output_cost_vcu = 0.0
    costs_by_model: Dict[str, Dict[str, Any]] = {}
    providers_by_model: Dict[str, str] = {}
    models_used: List[str] = list(usage_data.keys())
    venice_models_used = set()
    non_venice_models_used = set()

    for model, tokens in usage_data.items():
        available_models = app.state.model_list.get_model_list()
        # Find the model entry to get provider and cost
        model_entry = next((m for m in available_models if m["name"] == model), None)
        if not model_entry:
            app.ui.print_text(f"Warning: No model entry found for model {model}", PrintType.WARNING)
            continue
        provider = model_entry.get("provider", "")
        providers_by_model[model] = provider
        if provider == "venice":
            venice_models_used.add(model)
        else:
            non_venice_models_used.add(model)
        model_cost = cast(Dict[str, float], get_model_cost(model, available_models))
        if not model_cost:
            app.ui.print_text(f"Warning: No cost data available for model {model}", PrintType.WARNING)
            continue

        input_tokens = tokens.get("input_tokens", 0)
        output_tokens = tokens.get("output_tokens", 0)
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        # Calculate VCU costs (cost is per million tokens)
        input_cost_vcu = (input_tokens / 1_000_000) * model_cost["input_cost"]
        output_cost_vcu = (output_tokens / 1_000_000) * model_cost["output_cost"]
        total_cost_vcu = input_cost_vcu + output_cost_vcu

        # Calculate dollar costs
        vcu_dollar_value = cast(float, VCU_Value())
        input_cost_dollars = input_cost_vcu * vcu_dollar_value
        output_cost_dollars = output_cost_vcu * vcu_dollar_value
        total_cost_dollars = total_cost_vcu * vcu_dollar_value

        # Store costs for this model
        costs_by_model[model] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_vcu": input_cost_vcu,
            "output_cost_vcu": output_cost_vcu,
            "total_cost_vcu": total_cost_vcu,
            "input_cost_dollars": input_cost_dollars,
            "output_cost_dollars": output_cost_dollars,
            "total_cost_dollars": total_cost_dollars
        }

        # Add to totals (for all models)
        total_input_cost_vcu += input_cost_vcu
        total_output_cost_vcu += output_cost_vcu

    total_cost_vcu = total_input_cost_vcu + total_output_cost_vcu
    total_cost_dollars = total_cost_vcu * cast(float, VCU_Value())

    # Determine if all models used are Venice models
    all_venice = len(non_venice_models_used) == 0 and len(venice_models_used) > 0

    # Display total cost information
    app.ui.print_text("\n=== TOTAL SESSION COST ===", PrintType.HEADER)
    app.ui.print_text(f"Tokens used: {total_input_tokens} input, {total_output_tokens} output",
                   PrintType.INFO)
    # Only show VCU in total if all models used are Venice models
    if all_venice:
        app.ui.print_text(f"Total cost: ${total_cost_dollars:.4f} ({total_cost_vcu:.4f} VCU)", PrintType.INFO)
        app.ui.print_text(f"Input cost: ${(total_input_cost_vcu * cast(float, VCU_Value())):.4f} ({total_input_cost_vcu:.4f} VCU)", PrintType.INFO)
        app.ui.print_text(f"Output cost: ${(total_output_cost_vcu * cast(float, VCU_Value())):.4f} ({total_output_cost_vcu:.4f} VCU)", PrintType.INFO)
    else:
        app.ui.print_text(f"Total cost: ${total_cost_dollars:.4f}", PrintType.INFO)
        app.ui.print_text(f"Input cost: ${(total_input_cost_vcu * cast(float, VCU_Value())):.4f}", PrintType.INFO)
        app.ui.print_text(f"Output cost: ${(total_output_cost_vcu * cast(float, VCU_Value())):.4f}", PrintType.INFO)

    # Display cost breakdown by model
    app.ui.print_text("\n=== COST BREAKDOWN BY MODEL ===", PrintType.HEADER)

    for model, cost_data in costs_by_model.items():
        provider = providers_by_model.get(model, "")
        show_vcu = provider == "venice"
        app.ui.print_text(f"\nModel: {model}", PrintType.HEADER)
        app.ui.print_text(f"Tokens used: {cost_data['input_tokens']} input, {cost_data['output_tokens']} output", PrintType.INFO)
        app.ui.print_text(handle_cost_format_cost_line("Total cost", cost_data['total_cost_dollars'], cost_data['total_cost_vcu'], show_vcu), PrintType.INFO)
        app.ui.print_text(handle_cost_format_cost_line("Input cost", cost_data['input_cost_dollars'], cost_data['input_cost_vcu'], show_vcu), PrintType.INFO)
        app.ui.print_text(handle_cost_format_cost_line("Output cost", cost_data['output_cost_dollars'], cost_data['output_cost_vcu'], show_vcu), PrintType.INFO)
