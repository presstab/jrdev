import logging
from typing import Any, Awaitable, Callable, Dict, List, Protocol

# Import subcommand handlers
from jrdev.commands.git_config import (
    DEFAULT_GIT_CONFIG,
    get_git_config,
    handle_git_config_get,
    handle_git_config_list,
    handle_git_config_set,
)
from jrdev.commands.git_pr import handle_git_pr_review, handle_git_pr_summary
from jrdev.ui.ui import COLORS, PrintType


# Define a Protocol for Application to avoid circular imports
class Application(Protocol):
    logger: logging.Logger
    state: Any
    ui: Any


# Type for command handlers
CommandHandler = Callable[[Application, List[str], str], Awaitable[None]]

# Git subcommand registry using same pattern as application.py
# This is a simple flat dictionary with clear naming conventions
GIT_SUBCOMMANDS: Dict[str, CommandHandler] = {}


async def handle_git(app: Application, args: List[str], worker_id: str) -> None:
    """
    Entry point for all Git-related operations: configuration management and PR analysis.

    Usage:
      # Git configuration commands
      /git config list
          List all JrDev Git configuration keys and their current values.
      /git config get <key>
          Retrieve the value of a specific configuration key (e.g., base_branch).
      /git config set <key> <value> [--confirm]
          Update a configuration key. Use --confirm to override format warnings.

      # Pull-request commands
      /git pr summary [custom prompt]
          Generate a high-level summary of your current branch’s diff against the configured base branch.
      /git pr review [custom prompt]
          Generate a detailed code review of your current branch’s diff, including context from project files.

    Subcommand details:
      config:
        list                        - Show all JrDev git config values.
        get   <key>                 - Show the value of one key.
        set   <key> <value> [--confirm]
                                    - Change a config value (e.g. base_branch).
      pr:
        summary [prompt]            - Create a pull-request summary.
        review  [prompt]            - Create a detailed PR code review.

    Examples:
      /git config list
      /git config get base_branch
      /git config set base_branch origin/main
      /git pr summary "What changed in this feature branch?"
      /git pr review "Please review the latest security fixes."
    """
    # If no arguments provided, show git command help
    if len(args) == 1:
        show_git_help(app)
        return

    # Parse the subcommand structure (git <cmd> <subcmd>)
    cmd_parts = args[1:]
    if not cmd_parts:
        show_git_help(app)
        return

    # Look for pattern matching "git pr summary" or "git config get"
    if len(cmd_parts) >= 2:
        # Construct command key like "pr_summary" or "config_get"
        subcommand = f"{cmd_parts[0]}_{cmd_parts[1]}"

        if subcommand in GIT_SUBCOMMANDS:
            # Found a specific handler (e.g., git_pr_summary)
            await GIT_SUBCOMMANDS[subcommand](app, args, worker_id)
            return

    # If there's no multi-part handler or it's a single command
    subcommand = cmd_parts[0]

    # Check if there's a handler for this command
    if subcommand in GIT_SUBCOMMANDS:
        await GIT_SUBCOMMANDS[subcommand](app, args, worker_id)
    else:
        # Unknown command
        app.ui.print_text(f"Unknown git subcommand: {subcommand}", PrintType.ERROR)
        show_git_help(app)


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


def show_git_help(app: Application) -> None:
    """Display help text for the git command."""
    app.ui.print_text("Git Command Help", PrintType.HEADER)
    app.ui.print_text("Prerequisites:", PrintType.INFO)
    app.ui.print_text("• Git must be installed and available in your terminal PATH", PrintType.INFO)
    app.ui.print_text("• Repository must be initialized with git", PrintType.INFO)

    app.ui.print_text("\nFirst Time Setup:", PrintType.INFO)
    app.ui.print_text("1. Configure base branch for comparisons:", PrintType.INFO)
    app.ui.print_text(f"   {COLORS['BOLD']}/git config set base_branch origin/main{COLORS['RESET']}", PrintType.INFO)
    app.ui.print_text("   (Replace 'main' with your default branch name if different)", PrintType.INFO)
    app.ui.print_text("2. Fetch latest changes from remote (outside of JrDev):", PrintType.INFO)
    app.ui.print_text("   git fetch origin", PrintType.INFO)

    app.ui.print_text("\nPR Preparation:", PrintType.INFO)
    app.ui.print_text("• Checkout your feature branch (outside of JrDev): git checkout <your-branch>", PrintType.INFO)
    app.ui.print_text(
        "• Ensure base branch exists locally (outside of JrDev): git fetch origin <base-branch>", PrintType.INFO
    )
    app.ui.print_text("• Resolve any merge conflicts before generating PR content", PrintType.WARNING)

    app.ui.print_text("\nAvailable git commands:", PrintType.INFO)

    # Check for PR commands
    if any(cmd.startswith("pr_") for cmd in GIT_SUBCOMMANDS):
        # Format the command part (will be rendered in blue)
        app.ui.print_text(f"  {format_git_command_with_args('/git pr')}", PrintType.COMMAND, end="")
        # Description text (plain style like in help command)
        app.ui.print_text(" - Pull Request related commands: create a PR summary, or create a PR review")

    # Check for config commands
    if any(cmd.startswith("config_") for cmd in GIT_SUBCOMMANDS):
        # Format the command part (will be rendered in blue)
        app.ui.print_text(f"  {format_git_command_with_args('/git config')}", PrintType.COMMAND, end="")
        # Description text (plain style like in help command)
        app.ui.print_text(" - Configure git settings")


def show_subcommand_help(app: Application, subcommand: str) -> None:
    """Display help for a specific subcommand."""

    if subcommand == "pr":
        app.ui.print_text("Git PR Commands", PrintType.HEADER)
        app.ui.print_text("Requirements:", PrintType.INFO)
        app.ui.print_text("• Current branch must contain your PR changes", PrintType.INFO)
        app.ui.print_text("• Base branch should be fetched from remote", PrintType.INFO)
        app.ui.print_text("• No uncommitted changes or merge conflicts", PrintType.WARNING)

        app.ui.print_text("\nUsage Tips:", PrintType.INFO)
        app.ui.print_text(
            f"1. First configure base branch: {COLORS['BOLD']}/git config set base_branch origin/main{COLORS['RESET']}",
            PrintType.INFO,
        )
        app.ui.print_text("2. Fetch latest base branch: git fetch origin <base-branch>", PrintType.INFO)
        app.ui.print_text("3. Checkout your PR branch: git checkout <your-feature-branch>", PrintType.INFO)
        app.ui.print_text("4. Resolve any conflicts before generating content", PrintType.INFO)

        app.ui.print_text("\nAvailable PR commands:", PrintType.INFO)

        config = get_git_config(app)
        base_branch = config.get("base_branch", DEFAULT_GIT_CONFIG["base_branch"])

        # Display PR commands based on registry
        if "pr_summary" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            app.ui.print_text(
                f"  {format_git_command_with_args('/git pr summary', '[custom prompt]')}", PrintType.COMMAND, end=""
            )
            # Description text (plain style like in help command)
            app.ui.print_text(f" - Generate PR summary from diff with {base_branch}")

        if "pr_review" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            app.ui.print_text(
                f"  {format_git_command_with_args('/git pr review', '[custom prompt]')}", PrintType.COMMAND, end=""
            )
            # Description text (plain style like in help command)
            app.ui.print_text(f" - Generate detailed code review from diff with {base_branch}")

    elif subcommand == "config":
        app.ui.print_text("Git Config Commands", PrintType.HEADER)
        app.ui.print_text("Available config commands:", PrintType.INFO)

        # Display config commands based on registry
        if "config_list" in GIT_SUBCOMMANDS:
            # Command in blue
            app.ui.print_text(f"  {format_git_command_with_args('/git config list')}", PrintType.COMMAND, end="")
            # Description text (plain style like in help command)
            app.ui.print_text(" - List all git configuration values")

        if "config_get" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            app.ui.print_text(
                f"  {format_git_command_with_args('/git config get', '<key>')}", PrintType.COMMAND, end=""
            )
            # Description text (plain style like in help command)
            app.ui.print_text(" - Get a specific config value")

        if "config_set" in GIT_SUBCOMMANDS:
            # Command in blue with grey args
            app.ui.print_text(
                f"  {format_git_command_with_args('/git config set', '<key> <value>')}", PrintType.COMMAND, end=""
            )
            # Description text (plain style like in help command)
            app.ui.print_text(" - Set a config value")


# Function to register all git subcommands
def _register_subcommands() -> None:
    """Register all git subcommands."""
    # Register PR subcommands with clear naming pattern
    GIT_SUBCOMMANDS["pr_summary"] = handle_git_pr_summary
    GIT_SUBCOMMANDS["pr_review"] = handle_git_pr_review

    # Handle for "/git pr" - must return an awaitable
    async def show_pr_help(app: Application, _args: List[str], _worker_id: str) -> None:
        show_subcommand_help(app, "pr")

    GIT_SUBCOMMANDS["pr"] = show_pr_help

    # Register config subcommands with clear naming pattern
    GIT_SUBCOMMANDS["config_set"] = handle_git_config_set
    GIT_SUBCOMMANDS["config_get"] = handle_git_config_get
    GIT_SUBCOMMANDS["config_list"] = handle_git_config_list

    # Handle for "/git config" - must return an awaitable
    async def show_config_help(app: Application, _args: List[str], _worker_id: str) -> None:
        show_subcommand_help(app, "config")

    GIT_SUBCOMMANDS["config"] = show_config_help


# Initialize subcommands when the module is loaded
_register_subcommands()
