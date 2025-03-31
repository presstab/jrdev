#!/usr/bin/env python3

"""
Git command implementation for JrDev.
Provides git subcommands for PR summary, code review, and configuration.
"""

import logging
from typing import Awaitable, Callable, Dict, List, Protocol

from jrdev.ui.ui import PrintType, terminal_print, COLORS

# Import subcommand handlers
from jrdev.commands.git_config import (
    handle_git_config_get,
    handle_git_config_list,
    handle_git_config_set,
)
from jrdev.commands.git_pr import (
    handle_git_pr_review,
    handle_git_pr_summary,
)


# Define a Protocol for JrDevTerminal to avoid circular imports
class JrDevTerminal(Protocol):
    model: str
    logger: logging.Logger


# Type for command handlers
CommandHandler = Callable[[JrDevTerminal, List[str]], Awaitable[None]]

# Git subcommand registry using same pattern as terminal.py
# This is a simple flat dictionary with clear naming conventions
GIT_SUBCOMMANDS: Dict[str, CommandHandler] = {}


async def handle_git(terminal: JrDevTerminal, args: List[str]) -> None:
    """
    Handle the /git command with subcommands.
    
    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments
    """
    # If no arguments provided, show git command help
    if len(args) == 1:
        show_git_help()
        return

    # Parse the subcommand structure (git <cmd> <subcmd>)
    cmd_parts = args[1:]
    if not cmd_parts:
        show_git_help()
        return
        
    # Look for pattern matching "git pr summary" or "git config get"
    if len(cmd_parts) >= 2:
        # Construct command key like "pr_summary" or "config_get"
        subcommand = f"{cmd_parts[0]}_{cmd_parts[1]}"
        
        if subcommand in GIT_SUBCOMMANDS:
            # Found a specific handler (e.g., git_pr_summary)
            await GIT_SUBCOMMANDS[subcommand](terminal, args)
            return
            
    # If there's no multi-part handler or it's a single command
    subcommand = cmd_parts[0]
    
    # Check if there's a handler for this command
    if subcommand in GIT_SUBCOMMANDS:
        await GIT_SUBCOMMANDS[subcommand](terminal, args)
    else:
        # Unknown command
        terminal_print(f"Unknown git subcommand: {subcommand}", PrintType.ERROR)
        show_git_help()


def format_git_command_with_args(command, args=None):
    """
    Format a git command with grey arguments.
    
    Args:
        command: The base command (e.g., "/git pr")
        args: Optional arguments to add in grey (e.g., "<message>")
    
    Returns:
        Formatted command string with blue command and grey arguments
    """
    # Format command in blue (will be reset by PrintType.COMMAND)
    blue_command = command
    
    if args:
        # Format the arguments in grey and remove bold formatting
        grey_args = f"{COLORS['RESET']}{COLORS['BRIGHT_BLACK']}{args}"
        return f"{blue_command} {grey_args}"
    
    return blue_command


def show_git_help() -> None:
    """Display help text for the git command."""
    terminal_print("Git Command Help", PrintType.HEADER)
    terminal_print("Prerequisites:", PrintType.INFO)
    terminal_print("• Git must be installed and available in your terminal PATH", PrintType.INFO)
    terminal_print("• Repository must be initialized with git", PrintType.INFO)

    terminal_print("\nFirst Time Setup:", PrintType.INFO)
    terminal_print("1. Configure base branch for comparisons:", PrintType.INFO)
    terminal_print(f"   {COLORS['BOLD']}/git config set base_branch origin/main{COLORS['RESET']}", PrintType.INFO)
    terminal_print("   (Replace 'main' with your default branch name if different)", PrintType.INFO)
    terminal_print("2. Fetch latest changes from remote (outside of JrDev):", PrintType.INFO)
    terminal_print("   git fetch origin", PrintType.INFO)

    terminal_print("\nPR Preparation:", PrintType.INFO)
    terminal_print("• Checkout your feature branch (outside of JrDev): git checkout <your-branch>", PrintType.INFO)
    terminal_print("• Ensure base branch exists locally (outside of JrDev): git fetch origin <base-branch>", PrintType.INFO)
    terminal_print("• Resolve any merge conflicts before generating PR content", PrintType.WARNING)

    terminal_print("\nAvailable git commands:", PrintType.INFO)

    # Check for PR commands
    if any(cmd.startswith("pr_") for cmd in GIT_SUBCOMMANDS):
        # Format the command part (will be rendered in blue)
        terminal_print(
            f"  {format_git_command_with_args('/git pr')}",
            PrintType.COMMAND,
            end=""
        )
        # Description text (plain style like in help command)
        terminal_print(f" - Pull Request related commands: create a PR summary, or create a PR review")

    # Check for config commands
    if any(cmd.startswith("config_") for cmd in GIT_SUBCOMMANDS):
        # Format the command part (will be rendered in blue)
        terminal_print(
            f"  {format_git_command_with_args('/git config')}",
            PrintType.COMMAND,
            end=""
        )
        # Description text (plain style like in help command)
        terminal_print(f" - Configure git settings")


def show_subcommand_help(subcommand: str) -> None:
    """Display help for a specific subcommand."""
    from jrdev.commands.git_config import get_git_config, DEFAULT_GIT_CONFIG

    if subcommand == "pr":
        terminal_print("Git PR Commands", PrintType.HEADER)
        terminal_print("Requirements:", PrintType.INFO)
        terminal_print("• Current branch must contain your PR changes", PrintType.INFO)
        terminal_print("• Base branch should be fetched from remote", PrintType.INFO)
        terminal_print("• No uncommitted changes or merge conflicts", PrintType.WARNING)

        terminal_print("\nUsage Tips:", PrintType.INFO)
        terminal_print(
            f"1. First configure base branch: {COLORS['BOLD']}/git config set base_branch origin/main{COLORS['RESET']}",
            PrintType.INFO)
        terminal_print("2. Fetch latest base branch: git fetch origin <base-branch>", PrintType.INFO)
        terminal_print("3. Checkout your PR branch: git checkout <your-feature-branch>", PrintType.INFO)
        terminal_print("4. Resolve any conflicts before generating content", PrintType.INFO)

        terminal_print("\nAvailable PR commands:", PrintType.INFO)

        config = get_git_config()
        base_branch = config.get(
            "base_branch", DEFAULT_GIT_CONFIG["base_branch"]
        )

        # Display PR commands based on registry
        if "pr_summary" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            terminal_print(
                f"  {format_git_command_with_args('/git pr summary', '[custom prompt]')}",
                PrintType.COMMAND,
                end=""
            )
            # Description text (plain style like in help command)
            terminal_print(
                f" - Generate PR summary from diff with {base_branch}"
            )
            
        if "pr_review" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            terminal_print(
                f"  {format_git_command_with_args('/git pr review', '[custom prompt]')}",
                PrintType.COMMAND,
                end=""
            )
            # Description text (plain style like in help command)
            terminal_print(
                f" - Generate detailed code review from diff with {base_branch}"
            )
            
    elif subcommand == "config":
        terminal_print("Git Config Commands", PrintType.HEADER)
        terminal_print("Available config commands:", PrintType.INFO)

        # Display config commands based on registry
        if "config_list" in GIT_SUBCOMMANDS:
            # Command in blue
            terminal_print(
                f"  {format_git_command_with_args('/git config list')}",
                PrintType.COMMAND,
                end=""
            )
            # Description text (plain style like in help command)
            terminal_print(
                f" - List all git configuration values"
            )
            
        if "config_get" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            terminal_print(
                f"  {format_git_command_with_args('/git config get', '<key>')}",
                PrintType.COMMAND,
                end=""
            )
            # Description text (plain style like in help command)
            terminal_print(
                f" - Get a specific config value"
            )
            
        if "config_set" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            terminal_print(
                f"  {format_git_command_with_args('/git config set', '<key> <value>')}",
                PrintType.COMMAND,
                end=""
            )
            # Description text (plain style like in help command)
            terminal_print(
                f" - Set a config value"
            )


# Function to register all git subcommands
def _register_subcommands() -> None:
    """Register all git subcommands."""
    # Register PR subcommands with clear naming pattern
    GIT_SUBCOMMANDS["pr_summary"] = handle_git_pr_summary
    GIT_SUBCOMMANDS["pr_review"] = handle_git_pr_review
    
    # Handle for "/git pr" - must return an awaitable
    async def show_pr_help(terminal: JrDevTerminal, args: List[str]) -> None:
        show_subcommand_help("pr")
    GIT_SUBCOMMANDS["pr"] = show_pr_help

    # Register config subcommands with clear naming pattern
    GIT_SUBCOMMANDS["config_set"] = handle_git_config_set
    GIT_SUBCOMMANDS["config_get"] = handle_git_config_get
    GIT_SUBCOMMANDS["config_list"] = handle_git_config_list
    
    # Handle for "/git config" - must return an awaitable
    async def show_config_help(terminal: JrDevTerminal, args: List[str]) -> None:
        show_subcommand_help("config")
    GIT_SUBCOMMANDS["config"] = show_config_help


# Initialize subcommands when the module is loaded
_register_subcommands()