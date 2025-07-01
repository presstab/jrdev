import os
from typing import Dict, List

from jrdev.file_operations.confirmation import write_file_with_confirmation
from jrdev.file_operations.file_utils import get_file_contents
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.utils.treechart import generate_compact_tree

tools_list: Dict[str, str] = {
    "read_files": "Description: read a list of files. Args: list of file paths to read. Example: [src/main.py, "
    "src/model/data.py]",
    "get_file_tree": "Description: directory tree from the root of the project. Args: none",
    "write_file": "Description: write content to a file. Args: filename, content",
}


def read_files(files: List[str]) -> str:
    return get_file_contents(files)


def get_file_tree() -> str:
    current_dir = os.getcwd()
    ret = PromptManager().load("init/filetree_format")
    return f"{ret}\n{generate_compact_tree(current_dir, use_gitignore=True)}"


async def write_file(app, filename: str, content: str) -> str:
    result, _ = await write_file_with_confirmation(app, filename, content)
    return f"File write operation completed with status: {result}"
