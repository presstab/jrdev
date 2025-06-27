import subprocess
import shlex
from typing import Optional, Tuple, Dict, Any
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import generate_llm_response
from jrdev.utils.git_utils import get_staged_diff

import logging
logger = logging.getLogger("jrdev")

class GitPRServiceError(Exception):
    """Base exception for git PR service errors"""

    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.details = details


async def generate_pr_analysis(
        app: Any,
        base_branch: str,
        prompt_path: str,
        user_prompt: str = "",
        add_project_files: bool = False,
        worker_id: str = ""
) -> Tuple[Optional[str], Optional[Exception]]:
    """
    Core business logic for PR analysis generation
    Returns tuple: (response_text, error)
    """
    try:
        # Validate base branch exists
        safe_branch = shlex.quote(base_branch)
        subprocess.check_output(
            ["git", "rev-parse", "--verify", safe_branch],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5
        )

        # Get git diff
        diff_output = subprocess.check_output(
            ["git", "diff", safe_branch],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )

        if not diff_output:
            return None, GitPRServiceError(
                "No changes found in diff",
                {"base_branch": base_branch}
            )

        # Build messages
        builder = MessageBuilder(app)
        builder.start_user_section()
        if add_project_files:
            builder.add_project_files()
        builder.load_user_prompt(prompt_path)

        if user_prompt:
            builder.append_to_user_section(f"Additional instructions: {user_prompt}\n\n")

        builder.append_to_user_section(
            f"---PULL REQUEST DIFF BEGIN---\n{diff_output}\n---PULL REQUEST DIFF END---"
        )
        messages = builder.build()

        # Get LLM response
        response = await generate_llm_response(
            app,
            app.state.model,
            messages,
            task_id=worker_id,
            print_stream=False  # Let caller handle output
        )

        return str(response) if response else None, None

    except subprocess.CalledProcessError as e:
        error_details = {
            "command": e.cmd,
            "return_code": e.returncode,
            "output": e.output.strip(),
            "base_branch": base_branch
        }
        logger.error(f"{error_details}")
        return None, GitPRServiceError("Git command failed", error_details)

    except Exception as e:
        return None, GitPRServiceError("PR analysis failed", {"exception": e})


async def generate_commit_message(
    app: Any,
    worker_id: str = None
) -> Tuple[Optional[str], Optional[Exception]]:
    """
    Core business logic for commit message generation.
    Returns tuple: (response_text, error)
    """
    try:
        # Get staged git diff
        diff_output = get_staged_diff()

        if diff_output is None:  # Error occurred
            return None, GitPRServiceError(
                "Failed to get staged diff. Is git installed?",
                {}
            )

        if not diff_output.strip():
            return None, GitPRServiceError(
                "No staged changes found to commit.",
                {}
            )

        # Build messages
        builder = MessageBuilder(app)
        builder.start_user_section()
        builder.load_user_prompt("git/commit_message")

        builder.append_to_user_section(
            f"---GIT DIFF BEGIN---\n{diff_output}\n---GIT DIFF END---"
        )
        messages = builder.build()

        # Get LLM response
        response = await generate_llm_response(
            app,
            app.state.model,
            messages,
            task_id=worker_id,
            print_stream=False
        )

        return str(response) if response else None, None

    except Exception as e:
        return None, GitPRServiceError("Commit message generation failed", {"exception": e})
