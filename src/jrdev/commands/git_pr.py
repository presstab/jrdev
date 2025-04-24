#!/usr/bin/env python3

"""
Git PR commands for JrDev.
Provides functionality to generate PR summaries and code reviews based on git diffs.
"""

import logging
import subprocess
import shlex
from typing import Awaitable, Dict, List, Optional, Protocol, Any

from jrdev.commands.git_config import get_git_config, DEFAULT_GIT_CONFIG
from jrdev.llm_requests import stream_request
from jrdev.message_builder import MessageBuilder
from jrdev.ui.ui import PrintType

# Define a Protocol for Application to avoid circular imports
class ApplicationProtocol(Protocol):
    model: str
    logger: logging.Logger


async def _handle_git_pr_common(
    app: Any,
    args: List[str],
    prompt_path: str,
    operation_type: str,
    message_type: str,
    error_message: str,
    add_project_files: bool = False,
    worker_id: str = None
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
        f"Generating PR {operation_type} using diff with {base_branch}...",
        PrintType.INFO,
    )
    app.ui.print_text(
        f"Warning: Unresolved merge conflicts may affect diff results and show items that are not part of the PR",
        PrintType.WARNING
    )
    if user_prompt:
        app.ui.print_text(f"Using custom prompt: {user_prompt}", PrintType.INFO)
    app.ui.print_text(
        f"This uses the configured base branch. To change it, run: "
        f"/git config set base_branch <branch-name>",
        PrintType.INFO,
    )

    # Sanitize the base_branch parameter to prevent command injection
    # shlex.quote ensures the parameter is properly escaped for shell commands
    safe_base_branch = shlex.quote(base_branch)
    
    # Verify the base branch exists before attempting diff
    try:
        # Use git rev-parse --verify to check if the branch exists
        # Add a timeout to prevent hanging processes (5 seconds should be sufficient)
        subprocess.check_output(
            ["git", "rev-parse", "--verify", safe_base_branch],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,  # 5 second timeout
        )
    except subprocess.TimeoutExpired as timeout_err:
        # Log detailed error information for debugging
        app.logger.warning(
            f"Git branch verification timeout: branch='{base_branch}', safe_branch='{safe_base_branch}', "
            f"timeout={timeout_err.timeout}s, command={' '.join(timeout_err.cmd)}"
        )
        
        # Display user-friendly error messages in the terminal
        app.ui.print_text(
            f"Error: Command timed out while verifying branch '{base_branch}'.",
            PrintType.ERROR,
        )
        app.ui.print_text(
            "This could indicate a problem with the git repository or the branch name.",
            PrintType.WARNING,
        )
        return None
    except subprocess.CalledProcessError as cmd_err:
        # Extract structured information for logging
        error_output = cmd_err.output.strip() if cmd_err.output else "No error output"
        return_code = cmd_err.returncode
        command = ' '.join(cmd_err.cmd) if isinstance(cmd_err.cmd, list) else cmd_err.cmd
        
        # Log detailed error context
        app.logger.warning(
            f"Git branch verification failed: branch='{base_branch}', safe_branch='{safe_base_branch}', "
            f"return_code={return_code}, command='{command}', error_output='{error_output}'"
        )
        
        # Display user-friendly error messages in the terminal
        app.ui.print_text(
            f"Error: Base branch '{base_branch}' does not exist or is not a valid reference.",
            PrintType.ERROR,
        )
        app.ui.print_text(
            f"Please configure a valid branch with: /git config set base_branch <valid-branch>",
            PrintType.INFO,
        )
        app.ui.print_text(f"Original git error: {error_output}", PrintType.ERROR)
        return None

    # Get git diff using the sanitized base_branch
    try:
        # Add timeout to prevent hanging (30 seconds is reasonable for most diffs)
        diff_output = subprocess.check_output(
            ["git", "diff", safe_base_branch], 
            stderr=subprocess.STDOUT, 
            text=True,
            timeout=30  # 30 second timeout for diff (might take longer for large diffs)
        )
    except subprocess.TimeoutExpired as timeout_err:
        # Log detailed error information for debugging
        app.logger.warning(
            f"Git diff timeout: branch='{base_branch}', safe_branch='{safe_base_branch}', "
            f"timeout={timeout_err.timeout}s, command={' '.join(timeout_err.cmd)}"
        )
        
        # Display user-friendly error messages in the terminal
        app.ui.print_text(
            f"Error: Command timed out while generating diff with '{base_branch}'.",
            PrintType.ERROR,
        )
        app.ui.print_text(
            "This could indicate a very large diff or a problem with the git repository.",
            PrintType.WARNING,
        )
        app.ui.print_text(
            "Try setting a more specific base branch with: /git config set base_branch <branch>",
            PrintType.INFO,
        )
        return None
    except subprocess.CalledProcessError as cmd_err:
        # Extract structured information for logging
        error_output = cmd_err.output.strip() if cmd_err.output else "No error output"
        return_code = cmd_err.returncode
        command = ' '.join(cmd_err.cmd) if isinstance(cmd_err.cmd, list) else cmd_err.cmd
        
        # Log detailed error context
        app.logger.warning(
            f"Git diff command failed: branch='{base_branch}', safe_branch='{safe_base_branch}', "
            f"return_code={return_code}, command='{command}', error_output='{error_output}'"
        )
        
        # Display user-friendly error messages in the terminal
        app.ui.print_text(
            f"Error running git diff with branch '{base_branch}'", 
            PrintType.ERROR
        )
        app.ui.print_text(f"Git error: {error_output}", PrintType.ERROR)
        app.ui.print_text(
            "Make sure you have permission to access this repository and branch.",
            PrintType.INFO,
        )
        return None

    if not diff_output:
        app.ui.print_text(f"No changes found in diff with {base_branch}", PrintType.INFO)
        return None

    # Use MessageBuilder to construct messages
    builder = MessageBuilder(app)
    builder.start_user_section()
    if add_project_files:
        builder.add_project_files()
    builder.load_user_prompt(prompt_path)

    # Add user prompt if provided
    if user_prompt:
        builder.append_to_user_section(f"Additional instructions: {user_prompt}\n\n")

    builder.append_to_user_section(
        f"---PULL REQUEST DIFF BEGIN---\n{diff_output}\n---PULL REQUEST DIFF END---"
    )
    messages = builder.build()

    # Send request
    try:
        app.ui.print_text(
            f"\n{app.state.model} is creating {message_type}...\n",
            PrintType.PROCESSING,
        )
        # mypy: ignore[no-untyped-call]
        response = await stream_request(app, app.state.model, messages, task_id=worker_id, print_stream=True)
        return str(response) if response is not None else None
    except Exception as e:
        # Log detailed error context with traceback
        import traceback
        error_tb = traceback.format_exc()
        
        # Structured log with detailed context
        app.logger.error(
            f"{error_message}: type={type(e).__name__}, message={str(e)}, "
            f"operation={operation_type}, prompt_path={prompt_path}"
        )
        
        # Log the full traceback at debug level
        app.logger.debug(f"Traceback for {error_message}:\n{error_tb}")
        
        # User-friendly error message
        app.ui.print_text(
            f"An error occurred while creating the {message_type}.",
            PrintType.ERROR,
        )
        app.ui.print_text(
            f"Error details: {str(e)}",
            PrintType.ERROR,
        )
        return None


async def handle_git_pr_summary(app: Any, args: List[str], worker_id: str) -> None:
    """
    Generate a PR summary based on git diff with configured base branch.
    Args:
        app: The Application instance
        args: Command arguments
    """
    await _handle_git_pr_common(
        app=app,
        args=args,
        prompt_path="git/pr_summary",
        operation_type="summary",
        message_type="pull request summary",
        error_message="failed pull request summary",
        add_project_files=False,
        worker_id=worker_id
    )


async def handle_git_pr_review(app: Any, args: List[str], worker_id: str) -> None:
    """
    Generate a detailed PR code review based on git diff with configured base branch.
    Args:
        app: The Application instance
        args: Command arguments
    """
    await _handle_git_pr_common(
        app=app,
        args=args,
        prompt_path="git/pr_review",
        operation_type="code review",
        message_type="detailed code review",
        error_message="failed pull request review",
        add_project_files=True,
        worker_id=worker_id
    )