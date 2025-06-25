import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List, Protocol

from pydantic import BaseModel, Field, ValidationError

from jrdev.file_operations.file_utils import JRDEV_DIR
from jrdev.ui.colors import Colors
from jrdev.ui.ui import PrintType


# Define a Protocol for Application to avoid circular imports
class Application(Protocol):
    model: str
    logger: logging.Logger
    ui: Any


# Git config file path
GIT_CONFIG_PATH = os.path.join(JRDEV_DIR, "git_config.json")


# Pydantic model for git configuration
class GitConfig(BaseModel):
    """Schema for git configuration with validation."""

    base_branch: str = Field(default="origin/main", description="Default base branch for diff comparisons")

    # You can add more validated fields here in the future

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"  # Prevent unknown fields


# Default git configuration instance
DEFAULT_GIT_CONFIG = GitConfig().model_dump()


def get_git_config(app: Any) -> Dict[str, Any]:
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
            with open(GIT_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(default_config.model_dump(), f, indent=4)
            return default_config.model_dump()

        # Load and validate config from file
        with open(GIT_CONFIG_PATH, "r", encoding="utf-8") as f:
            # Parse JSON data
            json_data = json.load(f)

            # Validate against our schema
            validated_config = GitConfig.model_validate(json_data)
            return validated_config.model_dump()

    except json.JSONDecodeError as json_err:
        app.ui.print_text(f"Error parsing git config file: {str(json_err)}", PrintType.ERROR)
        app.ui.print_text("Using default configuration instead.", PrintType.WARNING)
    except ValidationError as validation_err:
        app.ui.print_text(f"Invalid git configuration format: {str(validation_err)}", PrintType.ERROR)
        app.ui.print_text("Config file contains invalid or unauthorized values.", PrintType.WARNING)
        app.ui.print_text("Using default configuration instead.", PrintType.WARNING)
    except FileNotFoundError as e:
        app.ui.print_text(f"Config file not found: {str(e)}", PrintType.ERROR)
    except PermissionError as e:
        app.ui.print_text(f"Permission error accessing git config: {str(e)}", PrintType.ERROR)
    except IOError as e:
        app.ui.print_text(f"I/O error reading git config: {str(e)}", PrintType.ERROR)
    except Exception as e:
        # Still keep a generic handler as a fallback, but with more details
        app.ui.print_text(
            f"Unexpected error loading git config ({type(e).__name__}): {str(e)}",
            PrintType.ERROR,
        )

    return GitConfig().model_dump()


def save_git_config(app: Any, config: Dict[str, Any]) -> bool:
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
            app.ui.print_text(f"Invalid git configuration: {str(validation_err)}", PrintType.ERROR)
            app.ui.print_text("Configuration contains invalid or unauthorized values.", PrintType.WARNING)
            return False

        # Create directory if it doesn't exist
        dir_path = os.path.dirname(GIT_CONFIG_PATH)
        os.makedirs(dir_path, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=dir_path, prefix=".git_config_", suffix=".tmp")

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
        app.ui.print_text(f"Error saving git config: {str(e)}", PrintType.ERROR)
        return False


async def handle_git_config_list(app: Any, _args: List[str], _worker_id: str) -> None:
    """
    List all git configuration values.
    Args:
        terminal: The Application instance
        args: Command arguments
    """
    config = get_git_config(app)

    app.ui.print_text("Git Configuration", PrintType.HEADER)
    app.ui.print_text("These settings control how JrDev's git commands behave:", PrintType.INFO)

    if not config:
        app.ui.print_text("No configuration values set. Using default values.", PrintType.INFO)
    else:
        # Display each configuration with description
        for key, value in config.items():
            if key == "base_branch":
                app.ui.print_text(f"{Colors.BOLD}{key}{Colors.RESET} = {value}", PrintType.INFO)
                app.ui.print_text(
                    "  Controls which git branch is used as the comparison base",
                    PrintType.INFO,
                )
                app.ui.print_text(
                    "  for generating PR summaries. Defaults to 'origin/main'.",
                    PrintType.INFO,
                )
                app.ui.print_text(
                    f"  Change with: {Colors.BOLD}/git config set base_branch <branch-name>{Colors.RESET}",
                    PrintType.INFO,
                )
            else:
                app.ui.print_text(f"{Colors.BOLD}{key}{Colors.RESET} = {value}", PrintType.INFO)


async def handle_git_config_get(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Get a specific git configuration value.
    Args:
        terminal: The Application instance
        args: Command arguments (including the key to get)
    """
    if len(args) < 2:
        app.ui.print_text("Missing key argument. Usage: /git config get <key>", PrintType.ERROR)
        app.ui.print_text("Available configuration keys:", PrintType.INFO)
        app.ui.print_text(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )
        return

    key = args[1]
    config = get_git_config(app)

    if key in config:
        app.ui.print_text(f"{Colors.BOLD}{key}{Colors.RESET} = {config[key]}", PrintType.INFO)

        # Additional information based on the key
        if key == "base_branch":
            app.ui.print_text(
                "This is the git branch used as comparison base for PR summaries.",
                PrintType.INFO,
            )
            app.ui.print_text("Examples of common values:", PrintType.INFO)
            app.ui.print_text("  origin/main   - GitHub default main branch", PrintType.INFO)
            app.ui.print_text("  origin/master - Traditional default branch", PrintType.INFO)
            app.ui.print_text("  origin/develop - Common development branch", PrintType.INFO)
    else:
        app.ui.print_text(f"Key '{key}' not found in git configuration", PrintType.ERROR)
        app.ui.print_text("Available configuration keys:", PrintType.INFO)
        app.ui.print_text(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )
        app.ui.print_text(
            f"Set with: {Colors.BOLD}/git config set {key} <value>{Colors.RESET}",
            PrintType.INFO,
        )


async def handle_git_config_set(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Set a git configuration value.
    Args:
        terminal: The Application instance
        args: Command arguments (including the key and value to set)
    """
    # Check if we have the correct number of arguments
    # args structure: ['/git', 'config', 'set', 'key', 'value']
    if len(args) < 5:
        app.ui.print_text("Missing arguments. Usage: /git config set <key> <value>", PrintType.ERROR)
        app.ui.print_text("Available configuration keys:", PrintType.INFO)
        app.ui.print_text(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )
        app.ui.print_text("Example:", PrintType.INFO)
        app.ui.print_text("  /git config set base_branch origin/main", PrintType.INFO)
        return

    # Extract key and value from the correct positions in the args list
    key = args[3]
    value = args[4]

    # Handle special cases
    if key == "base_branch":
        # Validate the branch value (should start with origin/ or be a valid branch name)
        if "/" not in value and not value.startswith("origin/"):
            app.ui.print_text(
                f"Warning: '{value}' doesn't follow the typical remote branch format.",
                PrintType.WARNING,
            )
            app.ui.print_text(
                "Common formats are 'origin/main', 'origin/master', or 'origin/develop'.",
                PrintType.INFO,
            )
            app.ui.print_text(
                "You can still set this value, but it might not work as expected.",
                PrintType.INFO,
            )
            # Ask for confirmation
            app.ui.print_text(
                f"To confirm setting base_branch to '{value}', run: " f"/git config set base_branch {value} --confirm",
                PrintType.INFO,
            )

            # Check if --confirm flag is present as a separate argument
            # This prevents matching branch names that might contain "--confirm" as a substring
            has_confirm_flag = False
            for i in range(3, len(args)):  # Start at index 3 (after "set base_branch value")
                if args[i] == "--confirm":
                    has_confirm_flag = True
                    break

            if not has_confirm_flag:
                return

        # Get current value
        config = get_git_config(app)
        old_value = config.get(key, DEFAULT_GIT_CONFIG["base_branch"])

        # Save to config
        config[key] = value
        if save_git_config(app, config):
            app.ui.print_text(
                f"Base branch changed from '{old_value}' to '{value}'.",
                PrintType.SUCCESS,
            )
            app.ui.print_text(
                f"PR summary will now use 'git diff {value}' for comparison.",
                PrintType.INFO,
            )
            app.ui.print_text("Try it now with: /git pr summary", PrintType.INFO)
    else:
        app.ui.print_text(f"Unknown configuration key: {key}", PrintType.ERROR)
        app.ui.print_text("Available configuration keys:", PrintType.INFO)
        app.ui.print_text(
            "  base_branch - The git branch to compare against for PR summaries",
            PrintType.INFO,
        )
