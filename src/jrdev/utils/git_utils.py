import subprocess
import logging
import os
from typing import List, Tuple, Optional, Set

logger = logging.getLogger("jrdev")

def get_git_status() -> Tuple[List[str], List[str], Set[str]]:
    """
    Gets the git status and separates files into staged, unstaged, and untracked sets.
    Untracked files are included in the unstaged list. This function is designed
    to be the single source of truth for git status parsing.

    Returns:
        A tuple containing (staged_files, unstaged_files, untracked_files).
        staged_files and unstaged_files are sorted lists of unique file paths.
        untracked_files is a set of unique file paths for untracked files.
        Returns ([], [], set()) if git is not found, it's not a git repo, or an error occurs.
    """
    staged = set()
    unstaged = set()
    untracked = set()
    try:
        # Use porcelain v1 for a stable, script-friendly output
        status_output = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10
        )

        if not status_output:
            return [], [], set()

        for line in status_output.splitlines():
            status = line[:2]
            filepath = line[3:]

            # Handle renamed/copied files, which have a format like 'XY old -> new'
            # We are interested in the new path.
            if ' -> ' in filepath:
                filepath = filepath.split(' -> ')[1]

            if status == '??':
                untracked.add(filepath)

            index_status = status[0]
            work_tree_status = status[1]

            # A file is staged if the index status is not a space or '?'.
            # '?' is for untracked files, which are not in the index.
            if index_status not in (' ', '?'):
                logger.info(f"{filepath} is STAGED - INDEX_STATUS {index_status} STATUS:{status}")
                staged.add(filepath)

            # A file is unstaged if the work tree status is not a space,
            # or if the file is untracked ('??').
            if work_tree_status != ' ' or status == '??':
                unstaged.add(filepath)

    except subprocess.CalledProcessError as e:
        # This can happen if it's not a git repository.
        logger.error(f"Failed to get git status. Is this a git repository? Error: {e.output}")
        return [], [], set()
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in your PATH?")
        return [], [], set()
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting git status: {e}")
        return [], [], set()
        
    return sorted(list(staged)), sorted(list(unstaged)), untracked


def get_file_diff(filepath: str, staged: bool = False, is_untracked: bool = False) -> Optional[str]:
    """
    Gets the diff for a single file from git.

    Args:
        filepath: The path to the file.
        staged: If True, gets the diff for the staged version of the file.
        is_untracked: If True, treats the file as new and diffs against an empty source.

    Returns:
        The diff content as a string, or a formatted error string if an error occurs.
    """
    command: List[str]
    try:
        if is_untracked:
            # For untracked files, diff against an empty file to show all content as new.
            # This is a common pattern for showing the content of a new file as a diff.
            command = ["git", "diff", "--no-index", "--", os.devnull, filepath]
        else:
            command = ["git", "diff"]
            if staged:
                command.append("--staged")
            command.extend(["--", filepath])

        diff_output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15
        )
        return diff_output # Exit code 0 means no diff
    except subprocess.CalledProcessError as e:
        # `git diff` returns 1 if there are differences, which is not an error for us.
        if e.returncode == 1:
            return e.output
        
        # Other non-zero exit codes indicate a real error.
        logger.error(f"Failed to get git diff for '{filepath}' (exit code {e.returncode}): {e.output.strip()}")
        return f"Error getting diff for {filepath}:\n{e.output.strip()}"
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in your PATH?")
        return "Error: Git command not found. Is git installed and in your PATH?"
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting git diff for '{filepath}': {e}")
        return f"An unexpected error occurred while getting diff for {filepath}:\n{e}"

def get_current_branch() -> Optional[str]:
    """
    Gets the current git branch name.

    Returns:
        The current branch name as a string, or None if an error occurs.
    """
    try:
        branch_name = subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5
        ).strip()
        
        return branch_name
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get current branch. Is this a git repository? Error: {e.output.strip()}")
        return None
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in your PATH?")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting current branch: {e}")
        return None

def stage_file(filepath: str) -> bool:
    """
    Stages a specific file in git.

    Args:
        filepath: The path to the file to stage.

    Returns:
        True if the file was staged successfully, False otherwise.
    """
    try:
        subprocess.check_output(
            ["git", "add", "--", filepath],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10
        )
        logger.info(f"Successfully staged file: {filepath}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to stage file '{filepath}'. Error: {e.output.strip()}")
        return False
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in your PATH?")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while staging file '{filepath}': {e}")
        return False

def unstage_file(filepath: str) -> bool:
    """
    Unstages a specific file in git.

    Args:
        filepath: The path to the file to unstage.

    Returns:
        True if the file was unstaged successfully, False otherwise.
    """
    try:
        # Use 'git reset HEAD -- <filepath>' to unstage
        subprocess.check_output(
            ["git", "reset", "HEAD", "--", filepath],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10
        )
        logger.info(f"Successfully unstaged file: {filepath}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to unstage file '{filepath}'. Error: {e.output.strip()}")
        return False
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in your PATH?")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while unstaging file '{filepath}': {e}")
        return False

def reset_unstaged_changes(filepath: str) -> bool:
    """
    Resets unstaged changes for a specific file in git.

    This is equivalent to `git checkout -- <filepath>`.

    Args:
        filepath: The path to the file to reset.

    Returns:
        True if the file was reset successfully, False otherwise.
    """
    try:
        subprocess.check_output(
            ["git", "checkout", "--", filepath],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10
        )
        logger.info(f"Successfully reset unstaged changes for file: {filepath}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset unstaged changes for file '{filepath}'. Error: {e.output.strip()}")
        return False
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in your PATH?")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while resetting unstaged changes for file '{filepath}': {e}")
        return False

def perform_commit(message: str) -> Tuple[bool, Optional[str]]:
    """
    Performs a git commit with the given message.

    Args:
        message: The commit message.

    Returns:
        A tuple (success, error_message).
        success is True if the commit was successful, False otherwise.
        error_message is a string containing the error if the commit failed, otherwise None.
    """
    try:
        subprocess.check_output(
            ["git", "commit", "-m", message],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15
        )
        logger.info(f"Successfully committed with message: {message[:30]}...")
        return True, None
    except subprocess.CalledProcessError as e:
        error_output = e.output.strip()
        logger.error(f"Failed to commit. Error: {error_output}")
        return False, error_output
    except FileNotFoundError:
        error_msg = "Git command not found. Is git installed and in your PATH?"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred during commit: {e}"
        logger.error(error_msg)
        return False, error_msg

def get_staged_diff() -> Optional[str]:
    """
    Gets the diff for all staged files.

    Returns:
        The diff content as a string, or None if an error occurs.
        Returns an empty string if there are no staged changes.
    """
    command = ["git", "diff", "--staged"]
    try:
        # This will return an empty string if there's no diff, and exit with 0.
        diff_output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15
        )
        return diff_output
    except subprocess.CalledProcessError as e:
        # `git diff` returns 1 if there are differences, which is not an error for us.
        if e.returncode == 1:
            return e.output
        
        # Other non-zero exit codes indicate a real error.
        logger.error(f"Failed to get staged git diff (exit code {e.returncode}): {e.output.strip()}")
        return None
    except FileNotFoundError:
        logger.error("Git command not found. Is git installed and in your PATH?")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting staged git diff: {e}")
        return None
