#!/usr/bin/env python3

"""
Models command implementation for the JrDev terminal.
"""
from typing import Any, List, TypedDict, cast

from jrdev.models import AVAILABLE_MODELS
from jrdev.ui import terminal_print, PrintType


class ModelInfo(TypedDict):
    """Type definition for model information."""
    name: str
    is_think: bool
    input_cost: int
    output_cost: int
    context_tokens: int


async def handle_models(terminal: Any, args: List[str]) -> None:
    """
    Handle the /models command to list all available models.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal_print("Available models:", print_type=PrintType.INFO)

    # Sort models by total cost (input + output) in descending order
    models = cast(List[ModelInfo], AVAILABLE_MODELS)
    sorted_models = sorted(
        models,
        key=lambda model: model["input_cost"] + model["output_cost"],
        reverse=True
    )

    # Define table headers and format
    headers = ["Model", "Type", "Input Cost", "Output Cost", "Context"]
    model_col_width = max(len(model["name"]) for model in sorted_models) + 2
    type_col_width = 10  # "Reasoning" is 9 chars + 1 for padding
    cost_col_width = 12
    context_col_width = 12

    # Print table header
    header_format = (
        f"  {{:{model_col_width}}} | "
        f"{{:{type_col_width}}} | "
        f"{{:{cost_col_width}}} | "
        f"{{:{cost_col_width}}} | "
        f"{{:{context_col_width}}}"
    )
    terminal_print(header_format.format(*headers), print_type=PrintType.INFO)

    # Print separator
    separator = (
        f"  {'-' * model_col_width} | "
        f"{'-' * type_col_width} | "
        f"{'-' * cost_col_width} | "
        f"{'-' * cost_col_width} | "
        f"{'-' * context_col_width}"
    )
    terminal_print(separator, print_type=PrintType.INFO)

    # Print table rows
    for model in sorted_models:
        model_name = model["name"]
        is_think = model["is_think"]
        input_cost = model["input_cost"]
        output_cost = model["output_cost"]
        context_tokens = model["context_tokens"]

        think_status = "Reasoning" if is_think else "Standard"
        input_cost_str = f"${input_cost/1000:.3f}/1K"
        output_cost_str = f"${output_cost/1000:.3f}/1K"
        context_str = f"{context_tokens//1024}K"

        # Add asterisk for selected model
        prefix = "* " if model_name == terminal.model else "  "

        # Format the row with proper spacing
        row = (
            f"{prefix}{model_name:{model_col_width}} | "
            f"{think_status:{type_col_width}} | "
            f"{input_cost_str:{cost_col_width}} | "
            f"{output_cost_str:{cost_col_width}} | "
            f"{context_str:{context_col_width}}"
        )

        if model_name == terminal.model:
            terminal_print(row, print_type=PrintType.SUCCESS)
        else:
            terminal_print(row, print_type=PrintType.INFO)
