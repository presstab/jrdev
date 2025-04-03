"""Command implementation for cost tracking."""
from typing import List, Dict, Any, cast

from jrdev.model_utils import get_model_cost, VCU_Value
from jrdev.ui.ui import PrintType
from jrdev.usage import get_instance


async def handle_cost(app: Any, cmd_parts: List[str]) -> None:
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

    for model, tokens in usage_data.items():
        available_models = app.state.model_list.get_model_list()
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

        # Add to totals
        total_input_cost_vcu += input_cost_vcu
        total_output_cost_vcu += output_cost_vcu

    total_cost_vcu = total_input_cost_vcu + total_output_cost_vcu
    total_cost_dollars = total_cost_vcu * cast(float, VCU_Value())

    # Display total cost information
    app.ui.print_text("\n=== TOTAL SESSION COST ===", PrintType.HEADER)
    app.ui.print_text(f"Tokens used: {total_input_tokens} input, {total_output_tokens} output",
                   PrintType.INFO)
    app.ui.print_text(f"Total cost: ${total_cost_dollars:.4f} ({total_cost_vcu:.4f} VCU)", PrintType.INFO)
    app.ui.print_text(f"Input cost: ${(total_input_cost_vcu * cast(float, VCU_Value())):.4f} ({total_input_cost_vcu:.4f} VCU)", PrintType.INFO)
    app.ui.print_text(f"Output cost: ${(total_output_cost_vcu * cast(float, VCU_Value())):.4f} ({total_output_cost_vcu:.4f} VCU)", PrintType.INFO)

    # Display cost breakdown by model
    app.ui.print_text("\n=== COST BREAKDOWN BY MODEL ===", PrintType.HEADER)

    for model, cost_data in costs_by_model.items():
        app.ui.print_text(f"\nModel: {model}", PrintType.HEADER)
        app.ui.print_text(f"Tokens used: {cost_data['input_tokens']} input, {cost_data['output_tokens']} output", PrintType.INFO)
        app.ui.print_text(f"Total cost: ${cost_data['total_cost_dollars']:.4f} ({cost_data['total_cost_vcu']:.4f} VCU)", PrintType.INFO)
        app.ui.print_text(f"Input cost: ${cost_data['input_cost_dollars']:.4f} ({cost_data['input_cost_vcu']:.4f} VCU)", PrintType.INFO)
        app.ui.print_text(f"Output cost: ${cost_data['output_cost_dollars']:.4f} ({cost_data['output_cost_vcu']:.4f} VCU)", PrintType.INFO)
