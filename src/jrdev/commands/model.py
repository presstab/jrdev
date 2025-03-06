#!/usr/bin/env python3

"""
Model command implementation for the JrDev terminal.
"""
from jrdev.models import AVAILABLE_MODELS
from jrdev.ui import terminal_print, PrintType


async def handle_model(terminal, args):
    """
    Handle the /model command to change or display the current model.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments
    """
    if len(args) > 1:
        requested_model = args[1]
        if requested_model in AVAILABLE_MODELS:
            terminal.model = requested_model
            terminal_print(f"Model changed to: {terminal.model}", print_type=PrintType.SUCCESS)
        else:
            terminal_print(f"Unknown model: {requested_model}", print_type=PrintType.ERROR)
            terminal_print(f"Available models: {', '.join(AVAILABLE_MODELS)}", print_type=PrintType.INFO)
    else:
        terminal_print(f"Current model: {terminal.model}", print_type=PrintType.INFO)
        terminal_print(f"Available models: {', '.join(AVAILABLE_MODELS)}", print_type=PrintType.INFO)
        terminal_print("Usage: /model <model_name>", print_type=PrintType.INFO)
