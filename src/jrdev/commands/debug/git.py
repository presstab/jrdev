#!/usr/bin/env python3

"""
Debug functionality for git commands.
This module provides additional git-related commands that are only available in debug mode.
"""

import logging
from typing import Any, Awaitable, List, Protocol

from jrdev.commands.git_config import GitConfig, get_git_config
from jrdev.ui.ui import PrintType


# Define a Protocol for JrDevTerminal to avoid circular imports
class JrDevTerminal(Protocol):
    model: str
    logger: logging.Logger


async def handle_git_debug_config_dump(app: Any, args: List[str]) -> None:
    """
    Debug command to dump git configuration information including the validation schema.

    Args:
        app: The JrDevTerminal instance
        args: Command arguments
    """
    # Get current config
    config = get_git_config(app)

    # Get schema information
    schema = GitConfig.model_json_schema()

    app.ui.print_text("Git Config Debug Information", PrintType.HEADER)
    app.ui.print_text("Current Configuration:", PrintType.SUBHEADER)

    for key, value in config.items():
        app.ui.print_text(f"  {key} = {value}", PrintType.INFO)

    app.ui.print_text("\nSchema Validation Rules:", PrintType.SUBHEADER)

    # Display properties from schema
    for prop_name, prop_info in schema.get("properties", {}).items():
        app.ui.print_text(f"  {prop_name}:", PrintType.INFO)
        app.ui.print_text(f"    Type: {prop_info.get('type', 'unknown')}", PrintType.INFO)
        app.ui.print_text(f"    Default: {prop_info.get('default', 'none')}", PrintType.INFO)
        if "description" in prop_info:
            app.ui.print_text(f"    Description: {prop_info['description']}", PrintType.INFO)

    # Display additional schema information
    app.ui.print_text("\nSchema Constraints:", PrintType.SUBHEADER)
    if schema.get("additionalProperties", True):
        app.ui.print_text("  Additional properties: Allowed", PrintType.INFO)
    else:
        app.ui.print_text("  Additional properties: Forbidden", PrintType.INFO)


# Export handlers
__all__ = ["handle_git_debug_config_dump"]
