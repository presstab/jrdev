import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

from jrdev.file_operations.confirmation import write_file_with_confirmation
from jrdev.file_operations.file_utils import get_file_contents
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.web_scrape_service import WebScrapeService
from jrdev.services.web_search_service import WebSearchService
from jrdev.utils.treechart import generate_compact_tree

logger = logging.getLogger("jrdev")

tools_list: Dict[str, str] = {
    "read_files": "Description: read a list of files. Args: list of file paths to read. Example: [src/main.py, "
    "src/model/data.py]",
    "get_file_tree": "Description: directory tree from the root of the project. Args: none",
    "write_file": "Description: write content to a file. Args: filename, content",
    "web_search": """
        Description: searches the web for a query
        Args: list[str] | The first element of the list packs the entire search query string. All other elements ignored.
        Results: List of url's and a summary of their match.
    """,
    "web_scrape_url": """
        Description: attempts to download the content from the provided url and clean it up into a readable format. This can fail if the website has measures taken against machine readability.
        Args: list[str]
         args[0]: Full url to scrap.
         args[1]: (optional) Save file path. Only save file if specifically instructed to. Must include .md file extension. Example: "test_file.md".
        Results: Website content converted to markdown format.
    """,
    "terminal": """
        Description: Bash terminal access using python subprocess.check_output(args[0], shell=True).
        Args: list[str] | The first element of the list packs the entire command and args. All other elements ignored. Example Args: [\"git checkout -b new_feat\"]
        Results: Result can either be 1) the string output of the shell, or 2) if the user cancels the tool, a cancellation message.
        Terminal Rules:
            1. Verify Directory - Use ls (or similar low compute command) to identify directory and files if your task requires file or directory operations.
            2. Quote file paths that contain spaces. Example: src/main writeup.txt should be \"src/main writeup.txt\"
    """,
    "get_indexed_files_context": """
        Description: This project has key files summarized in a compact, token-efficient format. When needing to understand large scopes of the project, begin with these summaries.
        Args: (optional) file_paths: list[str]. If omitted, returns all indexed file summaries.
        Results: Summaries for files indexed by the project.
    """,
}


def read_files(files: List[str]) -> str:
    return get_file_contents(files)


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

    return subprocess.check_output(args[0], stderr=subprocess.STDOUT, text=True, timeout=30, shell=True)


def web_search(args: List[str]) -> str:
    if not args:
        return ""
    service = WebSearchService()
    return str(service.search(args[0]))


async def web_scrape_url(args: List[str]) -> str:
    """

    Args:
        args[0]: URL
        args[1]: (optional) save to path

    Returns:

    """
    if not args:
        logger.info("web_scrap_url: empty args")
        return ""

    logger.info("web_scrape_url: scraping %s", args[0])
    doc = await WebScrapeService().fetch_and_convert(args[0])
    if len(args) > 1:
        file_path = args[1]
        with open(file_path, "w", encoding="utf-8") as file:
            logger.info("web_scrape_url: writing results to %s", file_path)
            file.write(doc)
    return doc
