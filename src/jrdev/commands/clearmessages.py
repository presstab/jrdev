#!/usr/bin/env python3

"""
ClearMessages command implementation for the JrDev terminal.
"""

from typing import Any, List

from jrdev.ui import terminal_print, PrintType


async def handle_clearmessages(terminal: Any, args: List[str]) -> None:
    """
    Handle the /clearmessages command to clear conversation history for all models.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    # Count the number of models with message history
    models_with_messages = list(terminal.messages.keys())
    num_models = len(models_with_messages)
    
    # Clear all message histories
    terminal.messages = {}
    
    if num_models > 0:
        model_names = ", ".join(models_with_messages)
        terminal_print(f"Cleared message history for {num_models} model(s): {model_names}", 
                      print_type=PrintType.SUCCESS)
    else:
        terminal_print("No message history to clear.", print_type=PrintType.INFO)