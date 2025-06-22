import logging
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, ListView, ListItem, Label, RichLog, Button
from textual import on
from textual.events import Key

from jrdev.utils.git_utils import (
    get_file_diff,
    get_git_status,
    get_current_branch,
    stage_file,
    unstage_file,
    reset_unstaged_changes,
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
        height: 2fr;
        padding: 0;
        border: none;
    }

    #git-status-lists-layout {
        width: 1fr;
        max-width: 40;
        height: 100%;
        padding: 0;
        overflow-y: auto;
    }
    
    #git-diff-layout {
        width: 2fr;
        height: 100%;
        padding: 0 1;
        layout: vertical;
    }
    
    #unstage-buttons-layout {
        height:1;
        border: none;
        margin: 0;
        padding: 0;
    }

    #branch-label {
        height: 2;
        padding: 1 0 0 1;
    }

    .status-list-title {
        padding: 1 0 0 1;
        text-style: bold;
        color: $text;
        height: 2;
    }

    .confirmation-label {
        padding: 0 1;
        color: $text;
        height: 1;
    }

    #unstaged-files-list, #staged-files-list {
        border: round $panel;
        margin-bottom: 0;
        height: 1fr;
        overflow-x: auto;
    }

    #diff-log {
        height: 1fr;
        width: 100%;
        background: $surface-darken-1;
        border: round $panel;
        padding: 0 1;
    }
    
    .stage-buttons {
        max-width: 9;
        padding: 0;
        margin-left: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.button_stage = Button("Stage", id="stage-button", classes="stage-buttons")
        self.button_reset = Button("Reset", id="reset-button", classes="stage-buttons")
        self.button_unstage = Button("Unstage", id="unstage-button", classes="stage-buttons")

        # Confirmation widgets for reset
        self.reset_confirmation_label = Label("Reset this file?", id="reset-confirmation-label", classes="confirmation-label")
        self.reset_confirmation_label.display = False
        self.button_confirm_reset = Button("Reset", id="confirm-reset-button", variant="error", classes="stage-buttons")
        self.button_confirm_reset.display = False
        self.button_cancel_reset = Button("Cancel", id="cancel-reset-button", classes="stage-buttons")
        self.button_cancel_reset.display = False

    def compose(self) -> ComposeResult:
        """Compose the widget's layout."""
        with Horizontal():
            with Vertical(id="git-status-lists-layout"):
                yield Label("Branch: ", id="branch-label", classes="status-list-title")
                yield Label("Unstaged Files", classes="status-list-title")
                yield ListView(id="unstaged-files-list")
                with Horizontal(id="unstage-buttons-layout"):
                    yield self.button_stage
                    yield self.button_reset
                    yield self.reset_confirmation_label
                    yield self.button_confirm_reset
                    yield self.button_cancel_reset
                yield Label("Staged Files", classes="status-list-title")
                yield ListView(id="staged-files-list")
                yield self.button_unstage
            with Vertical(id="git-diff-layout"):
                yield Label("File Diff", id="file-label", classes="status-list-title")
                yield RichLog(id="diff-log", highlight=False, markup=True)

    async def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.refresh_git_status()
        self.disabled_buttons()

    def disabled_buttons(self):
        self.button_stage.disabled = True
        self.button_unstage.disabled = True
        self.button_reset.disabled = True

    def reset_file_label(self):
        file_label = self.query_one("#file-label", Label)
        file_label.update("File Diff")

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

        staged_list.can_focus = False
        unstaged_list.can_focus = False

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
        # If confirmation is active, cancel it to avoid weird UI states
        if self.button_confirm_reset.display:
            self._toggle_reset_confirmation(False)

        staged_list = self.query_one("#staged-files-list", ListView)
        unstaged_list = self.query_one("#unstaged-files-list", ListView)
        
        # Deselect item in the other list to avoid confusion
        if event.list_view.id == "staged-files-list":
            if unstaged_list.index is not None:
                unstaged_list.index = None

            # Disable unstaged list buttons
            self.button_stage.disabled = True
            self.button_reset.disabled = True
            # Enable staged list buttons
            self.button_unstage.disabled = False
        else: # unstaged-files-list
            if staged_list.index is not None:
                staged_list.index = None

            # Enable unstaged list buttons
            self.button_stage.disabled = False
            self.button_reset.disabled = False
            # Enable staged list buttons
            self.button_unstage.disabled = True


        item = event.item
        file_label = self.query_one("#file-label", Label)
        if not isinstance(item, FileListItem):
            file_label.update(f"File Diff:")
            return

        file_label.update(f"File Diff: [green]{item.filepath}[/]")

        diff_log = self.query_one("#diff-log", RichLog)
        diff_log.clear()

        diff_content = get_file_diff(item.filepath, staged=item.staged, is_untracked=item.is_untracked)

        diff_log.clear()
        if diff_content is None or not diff_content.strip():
             diff_log.write(f"No changes to display for [bold]{item.filepath}[/].")
             return

        # Reuse diff formatting from CodeConfirmationScreen
        formatted_lines = []
        for line in diff_content.splitlines():
            escaped_line = line.replace("[", "\\[")
            if line.startswith('+'):
                formatted_lines.append(f"[green]{escaped_line}[/green]")
            elif line.startswith('-'):
                formatted_lines.append(f"[red]{escaped_line}[/red]")
            elif line.startswith('@@'):
                formatted_lines.append(f"[cyan]{escaped_line}[/cyan]")
            else:
                formatted_lines.append(escaped_line)
        diff_log.write("\n".join(formatted_lines))

    @on(Button.Pressed, "#stage-button")
    def handle_stage_pressed(self):
        unstaged_list = self.query_one("#unstaged-files-list", ListView)
        if unstaged_list.index is not None:
            # In Textual, list_view.children is a NodeList, which is list-like
            item = unstaged_list.children[unstaged_list.index]
            if isinstance(item, FileListItem):
                if stage_file(item.filepath):
                    self.notify(f"Staged: {item.filepath}", severity="information")
                    self.refresh_git_status()
                    self.disabled_buttons()
                    self.reset_file_label()
                else:
                    self.notify(f"Failed to stage: {item.filepath}", severity="error")

    @on(Button.Pressed, "#unstage-button")
    def handle_unstaged_pressed(self):
        staged_list = self.query_one("#staged-files-list", ListView)
        if staged_list.index is not None:
            item = staged_list.children[staged_list.index]
            if isinstance(item, FileListItem):
                if unstage_file(item.filepath):
                    self.notify(f"Unstaged: {item.filepath}", severity="information")
                    self.refresh_git_status()
                    self.disabled_buttons()
                    self.reset_file_label()
                else:
                    self.notify(f"Failed to unstage: {item.filepath}", severity="error")

    def _toggle_reset_confirmation(self, show: bool) -> None:
        """Toggle visibility of reset confirmation controls."""
        self.reset_confirmation_label.display = show
        self.button_confirm_reset.display = show
        self.button_cancel_reset.display = show
        # Toggle original buttons
        self.button_stage.display = not show
        self.button_reset.display = not show

    @on(Button.Pressed, "#reset-button")
    def handle_reset_pressed(self):
        self._toggle_reset_confirmation(True)

    @on(Button.Pressed, "#confirm-reset-button")
    def handle_confirm_reset_pressed(self):
        unstaged_list = self.query_one("#unstaged-files-list", ListView)
        if unstaged_list.index is not None:
            item = unstaged_list.children[unstaged_list.index]
            if isinstance(item, FileListItem):
                if reset_unstaged_changes(item.filepath):
                    self.notify(f"Reset changes for: {item.filepath}", severity="information")
                    self.refresh_git_status()
                    self.disabled_buttons()
                    self.reset_file_label()
                else:
                    self.notify(f"Failed to reset changes for: {item.filepath}", severity="error")
        self._toggle_reset_confirmation(False)

    @on(Button.Pressed, "#cancel-reset-button")
    def handle_cancel_reset_pressed(self):
        self._toggle_reset_confirmation(False)
