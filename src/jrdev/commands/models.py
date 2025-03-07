#!/usr/bin/env python3

"""
Models command implementation for the JrDev terminal.
"""
from jrdev.models import AVAILABLE_MODELS
from jrdev.ui import terminal_print, PrintType


async def handle_models(terminal, args):
    """
    Handle the /models command to list all available models.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    terminal_print("Available models:", print_type=PrintType.INFO)
    
    for model in AVAILABLE_MODELS:
        model_name = model["name"]
        is_think = model["is_think"]
        input_cost = model["input_cost"]
        output_cost = model["output_cost"]
        
        think_status = "Supports <think> tags" if is_think else "No <think> tags"
        costs = f"Input: ${input_cost/1000:.4f}/1K tokens, Output: ${output_cost/1000:.4f}/1K tokens"
        
        if model_name == terminal.model:
            terminal_print(f"  * {model_name} - {think_status} - {costs}", print_type=PrintType.SUCCESS)
        else:
            terminal_print(f"  {model_name} - {think_status} - {costs}", print_type=PrintType.INFO)
