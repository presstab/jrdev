#!/usr/bin/env python3

"""
Git PR commands for JrDev.
Provides functionality to generate PR summaries and code reviews based on git diffs.
"""

import logging
from dataclasses import dataclass
from typing import Any, List, Optional, Protocol

from jrdev.commands.git_config import DEFAULT_GIT_CONFIG, get_git_config
from jrdev.services.git_pr_service import GitPRServiceError, generate_pr_analysis
from jrdev.ui.ui import PrintType


# Define a Protocol for Application to avoid circular imports
class ApplicationProtocol(Protocol):
    model: str
    logger: logging.Logger


@dataclass
class PrSettings:
    prompt_path: str
    operation_type: str
    message_type: str
    add_project_files: bool


async def _handle_git_pr_common(
    app: Any,
    args: List[str],
    settings: PrSettings,
    worker_id: str = "",
) -> Optional[str]:
    """
    Common helper function for PR operations.
    Args:
        app: The Application instance
        args: Command arguments
        prompt_path: Path to the prompt file
        operation_type: Type of operation being performed (for display)
        message_type: Type of message being created (for display)
        error_message: Error message prefix
        add_project_files: Whether to add project files to the message

    Returns:
        The response from the LLM as a string or None if an error occurred
    """
    # Get configured base branch
    config = get_git_config(app)
    base_branch = config.get("base_branch", DEFAULT_GIT_CONFIG["base_branch"])

    # Extract user prompt if provided
    user_prompt = " ".join(args[1:]) if len(args) > 1 else ""

    app.ui.print_text(
        f"Generating PR {settings.operation_type} using diff with {base_branch}...",
        PrintType.INFO,
    )
    app.ui.print_text(
        "Warning: Unresolved merge conflicts may affect diff results and show items that are not part of the PR",
        PrintType.WARNING,
    )
    if user_prompt:
        app.ui.print_text(f"Using custom prompt: {user_prompt}", PrintType.INFO)
    app.ui.print_text(
        "This uses the configured base branch. To change it, run: /git config set base_branch <branch-name>",
        PrintType.INFO,
    )

    response, error = await generate_pr_analysis(
        app=app,
        base_branch=base_branch,
        prompt_path=settings.prompt_path,
        user_prompt=user_prompt,
        add_project_files=settings.add_project_files,
        worker_id=worker_id,
    )

    if error:
        # Handle error display
        app.ui.print_text(f"Error: {error}", PrintType.ERROR)
        if isinstance(error, GitPRServiceError):
            app.logger.error(f"PR service error: {error.details}")
        return None

    # Display success
    app.ui.print_text(f"Generated {settings.message_type}:", PrintType.SUCCESS)
    app.ui.print_text(response, PrintType.INFO)
    return response


async def handle_git_pr_summary(app: Any, args: List[str], worker_id: str) -> None:
    """
    Generate a PR summary based on git diff with configured base branch.
    Args:
        app: The Application instance
        args: Command arguments
    """
    settings = PrSettings(
        prompt_path="git/pr_summary",
        operation_type="summary",
        message_type="pull request summary",
        add_project_files=False,
    )
    await _handle_git_pr_common(
        app=app,
        args=args,
        settings=settings,
        worker_id=worker_id,
    )


async def handle_git_pr_review(app: Any, args: List[str], worker_id: str) -> None:
    """
    Generate a detailed PR code review based on git diff with configured base branch.
    Args:
        app: The Application instance
        args: Command arguments
    """
    settings = PrSettings(
        prompt_path="git/pr_review",
        operation_type="code review",
        message_type="detailed code review",
        add_project_files=True,
    )
    await _handle_git_pr_common(
        app=app,
        args=args,
        settings=settings,
        worker_id=worker_id,
    )
