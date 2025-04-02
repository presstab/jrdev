#!/usr/bin/env python3

"""
Model command implementation for the JrDev terminal.
"""
from typing import List
from jrdev.ui.ui import terminal_print, PrintType


async def handle_model(app, args: List[str]):
    """
    Handle the /model command to change or display the current model.

    Args:
        app: The Application instance
        args: Command arguments
    """

    model_names = app.get_model_names()
    
    if len(args) > 1:
        requested_model = args[1]
        if requested_model in model_names:
            app.state.model = requested_model
            terminal_print(f"Model changed to: {app.state.model}", print_type=PrintType.SUCCESS)
        else:
            terminal_print(f"Unknown model: {requested_model}", print_type=PrintType.ERROR)
            terminal_print(f"Available models: {', '.join(model_names)}", print_type=PrintType.INFO)
    else:
        terminal_print(f"Current model: {app.state.model}", print_type=PrintType.INFO)
        terminal_print(f"Available models: {', '.join(model_names)}", print_type=PrintType.INFO)
        terminal_print("Usage: /model <model_name>", print_type=PrintType.INFO)
