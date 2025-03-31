#!/usr/bin/env python3

"""
Git configuration commands for JrDev.
Provides functionality to get, set, and list git configuration settings.
"""

import json
import os
import logging
from typing import Any, Awaitable, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field, ValidationError

from jrdev.colors import Colors
from jrdev.file_utils import JRDEV_DIR
from jrdev.ui.ui import PrintType, terminal_print

# Define a Protocol for JrDevTerminal to avoid circular imports
class JrDevTerminal(Protocol):
    model: str
    logger: logging.Logger

# Git config file path
GIT_CONFIG_PATH = os.path.join(JRDEV_DIR, "git_config.json")

# Pydantic model for git configuration
class GitConfig(BaseModel):
    """Schema for git configuration with validation."""
    base_branch: str = Field(
        default="origin/main",
        description="Default base branch for diff comparisons"
    )
    
    # You can add more validated fields here in the future
    
    class Config:
        """Pydantic model configuration."""
        extra = "forbid"  # Prevent unknown fields

# Default git configuration instance
DEFAULT_GIT_CONFIG = GitConfig().model_dump()


def get_git_config() -> Dict[str, Any]:
    """
    Load git configuration from the config file with validation.
    If the file doesn't exist, create it with default values.
    Uses Pydantic to validate the config against the GitConfig schema.

    Returns:
        Dict containing validated git configuration
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(GIT_CONFIG_PATH), exist_ok=True)

        # Check if config file exists, create if not
        if not os.path.exists(GIT_CONFIG_PATH):
            # Create a default config using the Pydantic model
            default_config = GitConfig()
            with open(GIT_CONFIG_PATH, "w") as f:
                json.dump(default_config.model_dump(), f, indent=4)
            return default_config.model_dump()

        # Load and validate config from file
        with open(GIT_CONFIG_PATH, "r") as f:
            try:
                # Parse JSON data
                json_data = json.load(f)
                
                # Validate against our schema
                validated_config = GitConfig.model_validate(json_data)
                return validated_config.model_dump()
                
            except json.JSONDecodeError as json_err:
                terminal_print(
                    f"Error parsing git config file: {str(json_err)}", PrintType.ERROR
                )
                terminal_print(
                    "Using default configuration instead.", PrintType.WARNING
                )
                return GitConfig().model_dump()
                
            except ValidationError as validation_err:
                terminal_print(
                    f"Invalid git configuration format: {str(validation_err)}", 
                    PrintType.ERROR
                )
                terminal_print(
                    "Config file contains invalid or unauthorized values.", 
                    PrintType.WARNING
                )
                terminal_print(
                    "Using default configuration instead.", 
                    PrintType.WARNING
                )
                return GitConfig().model_dump()

    except FileNotFoundError as e:
        terminal_print(f"Config file not found: {str(e)}", PrintType.ERROR)
        return GitConfig().model_dump()
    except PermissionError as e:
        terminal_print(
            f"Permission error accessing git config: {str(e)}", PrintType.ERROR
        )
        return GitConfig().model_dump()
    except IOError as e:
        terminal_print(f"I/O error reading git config: {str(e)}", PrintType.ERROR)
        return GitConfig().model_dump()
    except Exception as e:
        # Still keep a generic handler as a fallback, but with more details
        terminal_print(
            f"Unexpected error loading git config ({type(e).__name__}): {str(e)}",
            PrintType.ERROR,
        )
        return GitConfig().model_dump()


def save_git_config(config: Dict[str, Any]) -> bool:
    """
    Save git configuration to the config file using atomic write operations with validation.
    This prevents corruption if multiple processes attempt to write simultaneously.
    Uses Pydantic to validate the config against the GitConfig schema.

    Args:
        config: The configuration to save

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Validate config data against our schema before saving
        try:
            validated_config = GitConfig.model_validate(config)
        except ValidationError as validation_err:
            terminal_print(
                f"Invalid git configuration: {str(validation_err)}", 
                PrintType.ERROR
            )
            terminal_print(
                "Configuration contains invalid or unauthorized values.", 
                PrintType.WARNING
            )
            return False

        # Create directory if it doesn't exist
        dir_path = os.path.dirname(GIT_CONFIG_PATH)
        os.makedirs(dir_path, exist_ok=True)

        # Create a temporary file in the same directory
        import shutil
        import tempfile

        fd, temp_path = tempfile.mkstemp(
            dir=dir_path, prefix=".git_config_", suffix=".tmp"
        )

        try:
            # Write validated config to the temporary file
            with os.fdopen(fd, "w") as temp_file:
                # Use the validated model to ensure we only save validated data
                json.dump(validated_config.model_dump(), temp_file, indent=4)

            # Use shutil.move for atomic replacement
            # This is atomic on Unix and does the right thing on Windows
            shutil.move(temp_path, GIT_CONFIG_PATH)
            return True
        except Exception as inner_e:
            # Clean up the temp file if anything went wrong
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise inner_e
    except Exception as e:
        terminal_print(f"Error saving git config: {str(e)}", PrintType.ERROR)
        return False


async def handle_git_config_list(terminal: JrDevTerminal, args: List[str]) -> None:
    """
    List all git configuration values.
    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments
    """
    config = get_git_config()

    terminal_print("Git Configuration", PrintType.HEADER)
    terminal_print(
        "These settings control how JrDev's git commands behave:", PrintType.INFO
    )

    if not config:
        terminal_print(
            "No configuration values set. Using default values.", PrintType.INFO
        )
    else:
        # Display each configuration with description
        for key, value in config.items():
            if key == "base_branch":
                terminal_print(
                    f"{Colors.BOLD}{key}{Colors.RESET} = {value}", PrintType.INFO
                )
                terminal_print(
                    "  Controls which git branch is used as the comparison base",
                    PrintType.INFO,
                )
                terminal_print(
                    "  for generating PR summaries. Defaults to 'origin/main'.",
                    PrintType.INFO,
                )
                terminal_print(
                    f"  Change with: {Colors.BOLD}/git config set base_branch <branch-name>{Colors.RESET}",
                    PrintType.INFO,
                )
            else:
                terminal_print(
                    f"{Colors.BOLD}{key}{Colors.RESET} = {value}", PrintType.INFO
                )


async def handle_git_config_get(terminal: JrDevTerminal, args: List[str]) -> None:
    """
    Get a specific git configuration value.
    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (including the key to get)
    """
    if len(args) < 2:
        terminal_print(
            "Missing key argument. Usage: /git config get <key>", PrintType.ERROR
        )
        terminal_print("Available configuration keys:", PrintType.INFO)
        terminal_print(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )
        return

    key = args[1]
    config = get_git_config()

    if key in config:
        terminal_print(
            f"{Colors.BOLD}{key}{Colors.RESET} = {config[key]}", PrintType.INFO
        )

        # Additional information based on the key
        if key == "base_branch":
            terminal_print(
                "This is the git branch used as comparison base for PR summaries.",
                PrintType.INFO,
            )
            terminal_print("Examples of common values:", PrintType.INFO)
            terminal_print(
                "  origin/main   - GitHub default main branch", PrintType.INFO
            )
            terminal_print(
                "  origin/master - Traditional default branch", PrintType.INFO
            )
            terminal_print(
                "  origin/develop - Common development branch", PrintType.INFO
            )
    else:
        terminal_print(f"Key '{key}' not found in git configuration", PrintType.ERROR)
        terminal_print("Available configuration keys:", PrintType.INFO)
        terminal_print(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )
        terminal_print(
            f"Set with: {Colors.BOLD}/git config set {key} <value>{Colors.RESET}",
            PrintType.INFO,
        )


async def handle_git_config_set(terminal: JrDevTerminal, args: List[str]) -> None:
    """
    Set a git configuration value.
    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (including the key and value to set)
    """
    if len(args) < 3:
        terminal_print(
            "Missing arguments. Usage: /git config set <key> <value>", PrintType.ERROR
        )
        terminal_print("Available configuration keys:", PrintType.INFO)
        terminal_print(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )
        terminal_print("Example:", PrintType.INFO)
        terminal_print("  /git config set base_branch origin/main", PrintType.INFO)
        return

    key = args[1]
    value = args[2]

    # Handle special cases
    if key == "base_branch":
        # Validate the branch value (should start with origin/ or be a valid branch name)
        if "/" not in value and not value.startswith("origin/"):
            terminal_print(
                f"Warning: '{value}' doesn't follow the typical remote branch format.",
                PrintType.WARNING,
            )
            terminal_print(
                "Common formats are 'origin/main', 'origin/master', or 'origin/develop'.",
                PrintType.INFO,
            )
            terminal_print(
                "You can still set this value, but it might not work as expected.",
                PrintType.INFO,
            )
            # Ask for confirmation
            terminal_print(
                f"To confirm setting base_branch to '{value}', run: "
                f"/git config set base_branch {value} --confirm",
                PrintType.INFO,
            )

            # Check if --confirm flag is present as a separate argument
            # This prevents matching branch names that might contain "--confirm" as a substring
            has_confirm_flag = False
            for i in range(
                3, len(args)
            ):  # Start at index 3 (after "set base_branch value")
                if args[i] == "--confirm":
                    has_confirm_flag = True
                    break

            if not has_confirm_flag:
                return

        # Get current value
        config = get_git_config()
        old_value = config.get(key, DEFAULT_GIT_CONFIG["base_branch"])

        # Save to config
        config[key] = value
        if save_git_config(config):
            terminal_print(
                f"Base branch changed from '{old_value}' to '{value}'.",
                PrintType.SUCCESS,
            )
            terminal_print(
                f"PR summary will now use 'git diff {value}' for comparison.",
                PrintType.INFO,
            )
            terminal_print("Try it now with: /git pr summary", PrintType.INFO)
    else:
        terminal_print(f"Unknown configuration key: {key}", PrintType.ERROR)
        terminal_print("Available configuration keys:", PrintType.INFO)
        terminal_print(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )