#!/usr/bin/env python3

"""
Model command implementation for the JrDev terminal.
"""
from jrdev.models import get_available_models
from jrdev.ui.ui import terminal_print, PrintType


async def handle_model(terminal, args):
    """
    Handle the /model command to change or display the current model.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments
    """
    # Fetch models from the API or cache
    models = await get_available_models()
    model_names = [model["name"] for model in models]
    
    if len(args) > 1:
        requested_model = args[1]
        if requested_model in model_names:
            terminal.model = requested_model
            terminal_print(f"Model changed to: {terminal.model}", print_type=PrintType.SUCCESS)
        else:
            terminal_print(f"Unknown model: {requested_model}", print_type=PrintType.ERROR)
            terminal_print(f"Available models: {', '.join(model_names)}", print_type=PrintType.INFO)
    else:
        terminal_print(f"Current model: {terminal.model}", print_type=PrintType.INFO)
        terminal_print(f"Available models: {', '.join(model_names)}", print_type=PrintType.INFO)
        terminal_print("Usage: /model <model_name>", print_type=PrintType.INFO)
