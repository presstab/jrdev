import os
import subprocess
from typing import Any, Dict, List, Optional

from jrdev.file_operations.confirmation import write_file_with_confirmation
from jrdev.file_operations.file_utils import get_file_contents
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.utils.treechart import generate_compact_tree

tools_list: Dict[str, str] = {
    "read_files": "Description: read a list of files. Args: list of file paths to read. Example: [src/main.py, "
    "src/model/data.py]",
    "get_file_tree": "Description: directory tree from the root of the project. Args: none",
    "write_file": "Description: write content to a file. Args: filename, content",
    "terminal": """
        Description: Bash terminal access using python subprocess.check_output(args[0], shell=True).
        Args: list[str] | The first element of the list packs the entire command and args. All other elements ignored. Example Args: [\"git checkout -b new_feat\"]
        Results: Result can either be 1) the string output of the shell, or 2) if the user cancels the tool, a cancellation message.
        Terminal Rules:
            1. Verify Directory - Use ls (or similar low compute command) to identify directory and files if your task requires file or directory operations.
            2. Quote file paths that contain spaces. Example: src/main writeup.txt should be \"src/main writeup.txt\"
    """,
    "get_project_summary": "Description: Returns the project's high-level overview and coding conventions. Args: none",
    "get_indexed_files_context": "Description: Returns summaries for files indexed by the project. Args: (optional) file_paths: list[str]. If omitted, returns all indexed file summaries.",
}


def read_files(files: List[str]) -> str:
    return get_file_contents(files)


def get_project_summary(app: Any) -> str:
    """
    Gets the project summary, including overview and conventions.
    """
    if not hasattr(app, "state") or not hasattr(app.state, "project_files"):
        return "Error: Project files not configured in application state."

    project_files = app.state.project_files.values()
    return get_file_contents(list(project_files))


def get_indexed_files_context(app: Any, files: Optional[List[str]] = None) -> str:
    """
    Gets context for indexed files.
    """
    if not hasattr(app, "state") or not hasattr(app.state, "context_manager"):
        return "Error: Context manager not configured in application state."

    context_manager = app.state.context_manager
    if not files:
        return context_manager.get_all_context()
    else:
        return context_manager.get_context_for_files(files)


def get_file_tree() -> str:
    current_dir = os.getcwd()
    ret = PromptManager().load("init/filetree_format")
    return f"{ret}\n{generate_compact_tree(current_dir, use_gitignore=True)}"


async def write_file(app, filename: str, content: str) -> str:
    result, _ = await write_file_with_confirmation(app, filename, content)
    return f"File write operation completed with status: {result}"


def terminal(args: List[str]) -> str:
    if not args:
        return ""

    return subprocess.check_output(
        args[0],
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        shell=True
    )