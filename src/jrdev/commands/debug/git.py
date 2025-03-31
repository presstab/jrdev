#!/usr/bin/env python3

"""
Debug functionality for git commands.
This module provides additional git-related commands that are only available in debug mode.
"""

import logging
from typing import Awaitable, List, Protocol

from jrdev.commands.git_config import get_git_config, GitConfig
from jrdev.ui.ui import PrintType, terminal_print


# Define a Protocol for JrDevTerminal to avoid circular imports
class JrDevTerminal(Protocol):
    model: str
    logger: logging.Logger


async def handle_git_debug_config_dump(terminal: JrDevTerminal, args: List[str]) -> None:
    """
    Debug command to dump git configuration information including the validation schema.
    
    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments
    """
    # Get current config
    config = get_git_config()
    
    # Get schema information
    schema = GitConfig.model_json_schema()
    
    terminal_print("Git Config Debug Information", PrintType.HEADER)
    terminal_print("Current Configuration:", PrintType.SUBHEADER)
    
    for key, value in config.items():
        terminal_print(f"  {key} = {value}", PrintType.INFO)
    
    terminal_print("\nSchema Validation Rules:", PrintType.SUBHEADER)
    
    # Display properties from schema
    for prop_name, prop_info in schema.get("properties", {}).items():
        terminal_print(f"  {prop_name}:", PrintType.INFO)
        terminal_print(f"    Type: {prop_info.get('type', 'unknown')}", PrintType.INFO)
        terminal_print(f"    Default: {prop_info.get('default', 'none')}", PrintType.INFO)
        if "description" in prop_info:
            terminal_print(f"    Description: {prop_info['description']}", PrintType.INFO)
    
    # Display additional schema information
    terminal_print("\nSchema Constraints:", PrintType.SUBHEADER)
    if schema.get("additionalProperties", True):
        terminal_print("  Additional properties: Allowed", PrintType.INFO)
    else:
        terminal_print("  Additional properties: Forbidden", PrintType.INFO)


# Export handlers
__all__ = ["handle_git_debug_config_dump"]