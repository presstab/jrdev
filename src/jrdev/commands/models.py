#!/usr/bin/env python3

"""
Models command implementation for the JrDev terminal.
"""
from jrdev.models import AVAILABLE_MODELS


async def handle_models(terminal, args):
    """
    Handle the /models command to list all available models.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (unused)
    """
    print("Available models:")
    for model in AVAILABLE_MODELS:
        print(f"  {model}")
