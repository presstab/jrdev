import logging
from typing import Any

from jrdev.ui.tui.model_listview import ModelListView
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import (
    Static,
    ListView,
    ListItem,
    Label,
    RichLog,
    Button,
    TextArea,
    LoadingIndicator,
)
from textual import on, work
from textual.worker import Worker, WorkerState

from jrdev.services.git_pr_service import generate_commit_message, GitPRServiceError
from jrdev.utils.git_utils import (
    get_file_diff,
    get_git_status,
    get_current_branch,
    stage_file,
    unstage_file,
    reset_unstaged_changes,
    perform_commit,
    get_commit_history,
    get_commit_diff,
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

class CommitListItem(ListItem):
    """A ListItem that holds a commit hash."""

    def __init__(self, commit_hash: str, commit_subject: str) -> None:
        super().__init__(Label(f"[yellow]{commit_hash}[/] {commit_subject}"))
        self.commit_hash = commit_hash

class GitOverviewWidget(Static):
    """A widget to display git status and file diffs."""

    DEFAULT_CSS = """
    GitOverviewWidget {
        layout: horizontal;
        height: 2fr;
        padding: 0;
        margin: 0;
        border: none;
    }
    
    #main-layout {
        border: none;
        margin: 0;
        padding: 0;
        height: 100%;
    }

    #git-status-lists-layout {
        width: 1fr;
        max-width: 40;
        height: 100%;
        padding: 0;
    }
    
    #git-diff-layout {
        width: 2fr;
        height: 100%;
        padding: 0 1;
        layout: vertical;
    }

    #diff-view {
        height: 1fr;
        width: 100%;
        layout: vertical;
        padding: 0;
        border: none;
        margin: 0;
    }

    #commit-view {
        height: 1fr;
        width: 100%;
        display: none; /* Hidden by default */
        layout: vertical;
        padding: 0;
        border: none;
        margin: 0;
    }

    #commit-message-textarea {
        height: 1fr;
        width: 100%;
        border: round $panel;
        margin: 0;
    }

    #commit-buttons-layout {
        height: auto;
        padding-top: 0;
        align-horizontal: left;
    }
    
    #generate-button-layout {
        height: 1;
        margin: 0;
        padding: 0;
        border: none;
    }

    #commit-buttons-layout Button {
        margin-right: 1;
    }
    
    #unstage-buttons-layout, #staged-buttons-layout {
        border: none;
        height: 1;
        margin: 0;
        padding: 0;
    }

    .top-labels {
        height: 1;
        padding: 0 0 0 1;
        margin: 0;
        text-style: bold;
        color: $text;
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
        overflow-y: auto;
    }
    
    #staged-list-layout, #unstaged-list-layout  {
        border: none;
        height: auto;
        max-height: 30%;
        min-height: 0;
        padding: 0;
        margin: 0;
    }
    
    #commit-history-list {
        border: round $panel;
        margin: 0;
        height: 1fr;
        overflow-x: auto;
        overflow-y: auto;
    }
    
    #commit-history-layout {
        border: none;
        height: 1fr;
        min-height: 30%;
        padding: 0 0 0 0;
        margin: 0;
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
        height: 1;
    }
    
    #generate-commit-msg-button {
        max-width: 25;
        padding: 0;
        margin-left: 1;
    }
    
    #loading-indicator {
        align-horizontal: left;
        max-width: 25;
        color: $accent;
    }
    #commit-model-list {
        layer: top;
        width: auto;
        border: round $accent;
    }
    .commit-select-model-btn {
        margin-left: 1;
        border: none;
        height: 100%;
        min-width: 10;
        width: auto;
    }
    """

    def __init__(self, core_app: Any):
        super().__init__()
        self.core_app = core_app
        self.button_stage = Button("Stage", id="stage-button", classes="stage-buttons")
        self.button_reset = Button("Reset", id="reset-button", classes="stage-buttons")
        self.button_unstage = Button("Unstage", id="unstage-button", classes="stage-buttons")
        self.button_commit = Button("Commit", id="commit-button", classes="stage-buttons")

        # Confirmation widgets for reset
        self.reset_confirmation_label = Label(
            "Reset this file?", id="reset-confirmation-label", classes="confirmation-label"
        )
        self.reset_confirmation_label.display = False
        self.button_confirm_reset = Button(
            "Reset", id="confirm-reset-button", variant="error", classes="stage-buttons"
        )
        self.button_confirm_reset.display = False
        self.button_cancel_reset = Button(
            "Cancel", id="cancel-reset-button", classes="stage-buttons"
        )
        self.button_cancel_reset.display = False

        # Commit view widgets
        self.commit_message_textarea = TextArea(
            id="commit-message-textarea"
        )
        self.button_generate_commit_msg = Button(
            "Generate Message", id="generate-commit-msg-button", variant="primary",
            tooltip="Have AI model generate commit message based on file diffs."
        )
        self.button_perform_commit = Button(
            "Create Commit", id="perform-commit-button", variant="success",
            tooltip="Create commit with the commit message above"
        )
        self.button_cancel_commit = Button("Cancel", id="cancel-commit-button")

        # Model selection for commit view
        self.commit_model_list = None
        self.commit_model_btn = None
        self._init_commit_model_selection()

        self.unstage_list_layout = Vertical(id="unstaged-list-layout")
        self.unstaged_list_title = Label("Unstaged Files", classes="status-list-title")
        self.unstaged_list = ListView(id="unstaged-files-list")
        self.unstaged_buttons_layout = Horizontal(id="unstage-buttons-layout")

    def _init_commit_model_selection(self):
        # Build the model list and button for commit view
        self.commit_model_btn = Button(
            self.core_app.state.model,
            classes="commit-select-model-btn",
            variant="primary",
            tooltip="Model used to generate commit message"
        )
        self.commit_model_list = ModelListView(
            id="commit-model-list",
            core_app=self.core_app,
            model_button=self.commit_model_btn,
            above_button=False
        )
        self.commit_model_list.visible = False

    def compose(self) -> ComposeResult:
        """Compose the widget's layout."""
        with Horizontal(id="main-layout"):

            with Vertical(id="git-status-lists-layout"):
                yield Label("Branch: ", id="branch-label", classes="top-labels")
                with self.unstage_list_layout:
                    yield self.unstaged_list_title
                    yield self.unstaged_list
                    with self.unstaged_buttons_layout:
                        yield self.button_stage
                        yield self.button_reset
                        yield self.reset_confirmation_label
                        yield self.button_confirm_reset
                        yield self.button_cancel_reset

                with Vertical(id="staged-list-layout"):
                    yield Label("Staged Files", classes="status-list-title")
                    yield ListView(id="staged-files-list")
                    with Horizontal(id="staged-buttons-layout"):
                        yield self.button_unstage
                        yield self.button_commit

                with Vertical(id="commit-history-layout"):
                    yield Label("Commit History", classes="status-list-title")
                    yield ListView(id="commit-history-list")
            with Vertical(id="git-diff-layout"):
                with Vertical(id="diff-view"):
                    yield Label("File Diff", id="file-label", classes="top-labels")
                    yield RichLog(id="diff-log", highlight=False, markup=True, auto_scroll=False)

                with Vertical(id="commit-view"):
                    yield Label("Commit Message: Enter or Generate Message", classes="status-list-title")
                    with Horizontal(id="generate-button-layout"):
                        yield self.button_generate_commit_msg
                        yield self.commit_model_btn
                    yield self.commit_model_list
                    yield self.commit_message_textarea
                    with Horizontal(id="commit-buttons-layout"):
                        yield self.button_perform_commit
                        yield self.button_cancel_commit

    async def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.refresh_git_status()

    def reset_file_label(self):
        file_label = self.query_one("#file-label", Label)
        file_label.update("File Diff")

    def refresh_git_status(self) -> None:
        """Fetches git status and populates the file lists."""
        # Disable buttons that require a selection, as the lists are being cleared.
        self.button_stage.disabled = True
        self.button_unstage.disabled = True
        self.button_reset.disabled = True

        branch_label = self.query_one("#branch-label", Label)
        branch_name = get_current_branch()
        logger.info(f"current branch: {branch_name}")
        branch_label.update(f"Branch: [bold green]{branch_name or 'N/A'}[/]")

        staged_list = self.query_one("#staged-files-list", ListView)
        unstaged_list = self.query_one("#unstaged-files-list", ListView)
        commit_history_list = self.query_one("#commit-history-list", ListView)
        diff_log = self.query_one("#diff-log", RichLog)

        staged_list.clear()
        unstaged_list.clear()
        commit_history_list.clear()
        diff_log.clear()

        staged_list.can_focus = False
        unstaged_list.can_focus = False
        commit_history_list.can_focus = False

        # Use git_utils to get staged, unstaged, and untracked files.
        # This is the single source of truth for git status.
        # The utility function handles errors and logging.
        staged_files, unstaged_files, untracked_files_set = get_git_status()

        # Enable/disable commit button based on staged files
        self.button_commit.disabled = not staged_files
        if not staged_files and self.query_one("#commit-view").styles.display == "block":
            self._toggle_commit_view(False)

        # Populate lists
        for filepath in unstaged_files:
            is_untracked = filepath in untracked_files_set
            unstaged_list.append(
                FileListItem(filepath, staged=False, is_untracked=is_untracked)
            )

        for filepath in staged_files:
            # Staged files can't be untracked.
            staged_list.append(FileListItem(filepath, staged=True, is_untracked=False))

        # Populate commit history
        commit_history = get_commit_history()
        for commit_hash, commit_subject in commit_history:
            commit_history_list.append(
                CommitListItem(commit_hash, commit_subject)
            )

        # manual adjustment of heights on staged lists
        if not staged_files:
            staged_list.styles.height = "auto"
        else:
            staged_list.styles.height = "1fr"
        if not unstaged_files:
            unstaged_list.styles.height = "auto"
        else:
            unstaged_list.styles.height = "1fr"

        # also update current model
        self.commit_model_btn.label = self.core_app.state.model

    @on(ListView.Selected, "#unstaged-files-list")
    @on(ListView.Selected, "#staged-files-list")
    @on(ListView.Selected, "#commit-history-list")
    def show_diff(self, event: ListView.Selected) -> None:
        """When a file or commit is selected, show its diff."""
        if event.list_view.id == "commit-model-list":
            return

        # If confirmation is active, cancel it to avoid weird UI states
        if self.button_confirm_reset.display:
            self._toggle_reset_confirmation(False)

        # If commit view is active, switch back to diff view
        if self.query_one("#commit-view").styles.display == "block":
            self._toggle_commit_view(False)

        staged_list = self.query_one("#staged-files-list", ListView)
        unstaged_list = self.query_one("#unstaged-files-list", ListView)
        commit_history_list = self.query_one("#commit-history-list", ListView)

        # Deselect items in other lists and manage button states
        if event.list_view.id == "staged-files-list":
            if unstaged_list.index is not None: unstaged_list.index = None
            if commit_history_list.index is not None: commit_history_list.index = None
            self.button_stage.disabled = True
            self.button_reset.disabled = True
            self.button_unstage.disabled = False
        elif event.list_view.id == "unstaged-files-list":
            if staged_list.index is not None: staged_list.index = None
            if commit_history_list.index is not None: commit_history_list.index = None
            self.button_stage.disabled = False
            self.button_reset.disabled = False
            self.button_unstage.disabled = True
        elif event.list_view.id == "commit-history-list":
            if staged_list.index is not None: staged_list.index = None
            if unstaged_list.index is not None: unstaged_list.index = None
            self.button_stage.disabled = True
            self.button_reset.disabled = True
            self.button_unstage.disabled = True

        item = event.item
        diff_log = self.query_one("#diff-log", RichLog)
        file_label = self.query_one("#file-label", Label)
        diff_log.clear()

        if isinstance(item, FileListItem):
            file_label.update(f"File Diff: [green]{item.filepath}[/]")
            diff_content = get_file_diff(
                item.filepath, staged=item.staged, is_untracked=item.is_untracked
            )
            if diff_content is None or not diff_content.strip():
                diff_log.write(f"No changes to display for [bold]{item.filepath}[/].")
                return

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

        elif isinstance(item, CommitListItem):
            file_label.update(f"Commit Diff: [yellow]{item.commit_hash}[/]")
            commit_diff_content = get_commit_diff(item.commit_hash)

            if commit_diff_content is None or not commit_diff_content.strip():
                diff_log.write(f"No diff to display for commit [bold]{item.commit_hash}[/].")
                return

            formatted_lines = []
            for line in commit_diff_content.splitlines():
                escaped_line = line.replace("[", "\\[")
                # Special formatting for git show output
                if line.startswith('commit '):
                    formatted_lines.append(f"[yellow]{escaped_line}[/yellow]")
                elif line.startswith('Author:') or line.startswith('Date:'):
                    formatted_lines.append(f"[blue]{escaped_line}[/blue]")
                elif line.startswith('+') and not line.startswith('+++'):
                    formatted_lines.append(f"[green]{escaped_line}[/green]")
                elif line.startswith('-') and not line.startswith('---'):
                    formatted_lines.append(f"[red]{escaped_line}[/red]")
                elif line.startswith('@@'):
                    formatted_lines.append(f"[cyan]{escaped_line}[/cyan]")
                else:
                    formatted_lines.append(escaped_line)
            diff_log.write("\n".join(formatted_lines))
        else:
            # Some other list item, maybe from a future list. Clear the view.
            file_label.update("File Diff")

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
                    self.notify(
                        f"Reset changes for: {item.filepath}", severity="information"
                    )
                    self.refresh_git_status()
                    self.reset_file_label()
                else:
                    self.notify(
                        f"Failed to reset changes for: {item.filepath}", severity="error"
                    )
        self._toggle_reset_confirmation(False)

    @on(Button.Pressed, "#cancel-reset-button")
    def handle_cancel_reset_pressed(self):
        self._toggle_reset_confirmation(False)

    def _toggle_commit_view(self, show: bool) -> None:
        """Toggle visibility of the commit message view."""
        self.query_one("#commit-view").styles.display = "block" if show else "none"
        self.query_one("#diff-view").styles.display = "none" if show else "block"
        if show:
            self.commit_message_textarea.focus()
            # Update model button label to current model
            self.commit_model_btn.label = self.core_app.state.model
            # Hide model list popup if open
            self.commit_model_list.visible = False
        else:
            try:
                self.query_one("#staged-files-list", ListView).focus()
            except Exception:
                pass

    @on(Button.Pressed, "#commit-button")
    def handle_commit_pressed(self):
        """Show the commit message UI."""
        self._toggle_commit_view(True)

    @on(Button.Pressed, "#cancel-commit-button")
    def handle_cancel_commit_pressed(self):
        """Hide the commit message UI and show the diff view."""
        self._toggle_commit_view(False)

    @on(Button.Pressed, "#perform-commit-button")
    def handle_perform_commit(self):
        """Performs the git commit with the message from the text area."""
        commit_message = self.commit_message_textarea.text
        if not commit_message.strip():
            self.notify("Commit message cannot be empty.", severity="error")
            return

        success, error_message = perform_commit(commit_message)

        if success:
            self.notify("Commit successful.", severity="information")
            self._toggle_commit_view(False)
            self.refresh_git_status()
            self.reset_file_label()
        else:
            self.notify(f"Commit failed: {error_message}", severity="error", timeout=10)

    @on(Button.Pressed, "#generate-commit-msg-button")
    async def handle_generate_commit_message(self):
        """Start the worker to generate a commit message."""
        button_container = self.query_one("#generate-button-layout")
        self.button_generate_commit_msg.display = False
        indicator = LoadingIndicator(id="loading-indicator")
        await button_container.mount(indicator)
        self.generate_commit_message_worker()

    @work(group="git_commit", exclusive=True)
    async def generate_commit_message_worker(self):
        """Worker to call the commit message generation service."""
        response, error = await generate_commit_message(
            app=self.core_app, worker_id=None
        )
        if error:
            if isinstance(error, GitPRServiceError):
                raise RuntimeError(
                    f"GitPRServiceError Details: {error.details}"
                )
            raise error
        return response

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker completion for commit message generation."""
        if event.worker.group != "git_commit":
            return

        if event.state == WorkerState.RUNNING or event.state == WorkerState.PENDING:
            return

        button_container = self.query_one("#generate-button-layout")
        try:
            indicator = button_container.query_one(LoadingIndicator)
            await indicator.remove()
        except Exception as e:
            logger.warning(f"Could not remove loading indicator: {e}")

        self.button_generate_commit_msg.display = True

        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if isinstance(result, str):
                self.commit_message_textarea.load_text(result)
                self.notify("Commit message generated.", severity="information")
            else:
                self.notify(
                    "Failed to generate commit message: No text received.",
                    severity="error",
                )
        elif event.state == WorkerState.ERROR:
            error = event.worker.error
            logger.error(f"Commit message generation worker failed: {error}")
            self.notify(
                f"Error generating message: {error}", severity="error", timeout=10
            )

    # --- Model selection popup for commit view ---
    @on(Button.Pressed, ".commit-select-model-btn")
    def handle_commit_model_select(self) -> None:
        self.commit_model_list.set_visible(not self.commit_model_list.visible)

    @on(ModelListView.ModelSelected, "#commit-model-list")
    def handle_commit_model_selection(self, selected: ModelListView.ModelSelected):
        model_name = selected.model
        self.core_app.set_model(model_name)
        self.commit_model_list.visible = False
        self.commit_model_btn.label = model_name
        self.commit_model_btn.styles.max_width = len(model_name) + 2
