import logging
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, ListView, ListItem, Label, RichLog
from textual import on
from textual.events import Key

from jrdev.utils.git_utils import (
    get_file_diff,
    get_git_status,
    get_current_branch,
    stage_file,
    unstage_file,
)

logger = logging.getLogger("jrdev")


class FileListItem(ListItem):
    """A ListItem that holds file path and git status."""
    def __init__(self, filepath: str, staged: bool, is_untracked: bool = False) -> None:
        # The Label will be the display part of the ListItem
        super().__init__(Label(filepath))
        self.filepath = filepath
        self.staged = staged
        self.is_untracked = is_untracked


class GitOverviewWidget(Static):
    """A widget to display git status and file diffs."""

    DEFAULT_CSS = """
    GitOverviewWidget {
        layout: horizontal;
        height: 1fr;
        padding: 0;
        border: none;
    }

    #git-status-lists {
        width: 35%;
        height: 100%;
        border-right: solid $panel;
        padding: 0 1;
        overflow-y: auto;
    }

    #branch-label {
        height: 1;
        padding: 1 0 0 1;
    }

    .status-list-title {
        padding: 1 0 0 1;
        text-style: bold;
        color: $text;
        height: 2;
    }

    #unstaged-files-list, #staged-files-list {
        border: round $panel;
        margin-bottom: 1;
        height: 1fr;
    }

    #git-diff-view {
        width: 65%;
        height: 100%;
        padding: 0 1;
        layout: vertical;
    }

    #diff-log {
        height: 1fr;
        background: $surface-darken-1;
        border: round $panel;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the widget's layout."""
        with Horizontal():
            with Vertical(id="git-status-lists"):
                yield Label("", id="branch-label")
                yield Label("Unstaged Files ('s' to stage)", classes="status-list-title")
                yield ListView(id="unstaged-files-list")
                yield Label("Staged Files ('u' to unstage)", classes="status-list-title")
                yield ListView(id="staged-files-list")
            with Vertical(id="git-diff-view"):
                yield Label("File Diff", classes="status-list-title")
                yield RichLog(id="diff-log", highlight=False, markup=True)

    async def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.refresh_git_status()

    def refresh_git_status(self) -> None:
        """Fetches git status and populates the file lists."""
        branch_label = self.query_one("#branch-label", Label)
        branch_name = get_current_branch()
        logger.info(f"current branch: {branch_name}")
        branch_label.update(f"Branch: [bold green]{branch_name or 'N/A'}[/]")

        staged_list = self.query_one("#staged-files-list", ListView)
        unstaged_list = self.query_one("#unstaged-files-list", ListView)
        diff_log = self.query_one("#diff-log", RichLog)

        staged_list.clear()
        unstaged_list.clear()
        diff_log.clear()

        # Use git_utils to get staged, unstaged, and untracked files.
        # This is the single source of truth for git status.
        # The utility function handles errors and logging.
        staged_files, unstaged_files, untracked_files_set = get_git_status()

        # Populate lists
        for filepath in unstaged_files:
            is_untracked = filepath in untracked_files_set
            unstaged_list.append(FileListItem(filepath, staged=False, is_untracked=is_untracked))
        
        for filepath in staged_files:
            # Staged files can't be untracked.
            staged_list.append(FileListItem(filepath, staged=True, is_untracked=False))

    @on(ListView.Selected)
    def show_diff(self, event: ListView.Selected) -> None:
        """When a file is selected, show its diff."""
        staged_list = self.query_one("#staged-files-list", ListView)
        unstaged_list = self.query_one("#unstaged-files-list", ListView)
        
        # Deselect item in the other list to avoid confusion
        if event.list_view.id == "staged-files-list":
            if unstaged_list.index is not None:
                unstaged_list.index = None
        else: # unstaged-files-list
            if staged_list.index is not None:
                staged_list.index = None

        item = event.item
        if not isinstance(item, FileListItem):
            return

        diff_log = self.query_one("#diff-log", RichLog)
        diff_log.clear()
        diff_log.write(f"Loading diff for [bold]{item.filepath}[/]...")

        diff_content = get_file_diff(item.filepath, staged=item.staged, is_untracked=item.is_untracked)

        diff_log.clear()
        if diff_content is None or not diff_content.strip():
             diff_log.write(f"No changes to display for [bold]{item.filepath}[/].")
             return

        # Reuse diff formatting from CodeConfirmationScreen
        formatted_lines = []
        for line in diff_content.splitlines():
            escaped_line = line.replace("[", "\\[").replace("]", "\\]")
            if line.startswith('+'):
                formatted_lines.append(f"[green]{escaped_line}[/green]")
            elif line.startswith('-'):
                formatted_lines.append(f"[red]{escaped_line}[/red]")
            elif line.startswith('@@'):
                formatted_lines.append(f"[cyan]{escaped_line}[/cyan]")
            else:
                formatted_lines.append(escaped_line)
        diff_log.write("\n".join(formatted_lines))

    def on_key(self, event: Key) -> None:
        """Handle key presses for staging and unstaging files."""
        if event.key == "s":
            unstaged_list = self.query_one("#unstaged-files-list", ListView)
            if unstaged_list.index is not None:
                # In Textual, list_view.children is a NodeList, which is list-like
                item = unstaged_list.children[unstaged_list.index]
                if isinstance(item, FileListItem):
                    if stage_file(item.filepath):
                        self.notify(f"Staged: {item.filepath}", severity="information")
                        self.refresh_git_status()
                    else:
                        self.notify(f"Failed to stage: {item.filepath}", severity="error")
        elif event.key == "u":
            staged_list = self.query_one("#staged-files-list", ListView)
            if staged_list.index is not None:
                item = staged_list.children[staged_list.index]
                if isinstance(item, FileListItem):
                    if unstage_file(item.filepath):
                        self.notify(f"Unstaged: {item.filepath}", severity="information")
                        self.refresh_git_status()
                    else:
                        self.notify(f"Failed to unstage: {item.filepath}", severity="error")
