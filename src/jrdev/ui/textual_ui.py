from jrdev.ui.ui import printtype_to_string
from textual import on
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, RadioSet
from textual.worker import Worker
from textual.color import Color
from jrdev.core.application import Application
from jrdev import __version__
from jrdev.ui.textual_events import TextualEvents
from jrdev.ui.tui.code_confirmation_screen import CodeConfirmationScreen
from jrdev.ui.tui.steps_screen import StepsScreen
from jrdev.ui.tui.code_edit_screen import CodeEditScreen
from jrdev.ui.tui.filtered_directory_tree import DirectoryWidget
from jrdev.ui.tui.api_key_entry import ApiKeyEntry
from jrdev.ui.tui.model_selection_widget import ModelSelectionWidget
from jrdev.ui.tui.task_monitor import TaskMonitor
from jrdev.ui.tui.terminal_output_widget import TerminalOutputWidget
from jrdev.ui.tui.input_widget import CommandTextArea
from jrdev.ui.tui.button_container import ButtonContainer
from jrdev.ui.tui.chat_list import ChatList
from jrdev.ui.tui.model_profile_widget import ModelProfileScreen
from jrdev.ui.tui.command_request import CommandRequest
from jrdev.ui.tui.chat_view_widget import ChatViewWidget
from jrdev.ui.tui.bordered_switcher import BorderedSwitcher
from jrdev.ui.tui.file_deletion_screen import FileDeletionScreen
from jrdev.ui.tui.settings_screen import SettingsScreen

from typing import Any, Generator, Set
import logging
logger = logging.getLogger("jrdev")

class JrDevUI(App[None]):
    CSS_PATH = "textual_ui.tcss"

    def __init__(self):
        super().__init__()
        self.settings_screen = None
        self.chat_tasks: Set[str] = set()

    def compose(self) -> Generator[Any, None, None]:
        self.jrdev = Application()
        self.jrdev.ui = TextualEvents(self)
        self.title = "JrDev Terminal"
        self.jrdev.setup()
        self.vlayout_terminal = Vertical()
        self.vlayout_right = Vertical()
        self.vlayout_left = Vertical()
        self.terminal_output_widget = TerminalOutputWidget(id="terminal_output_container")
        self.task_monitor = TaskMonitor(self.jrdev)
        self.directory_widget = DirectoryWidget(core_app=self.jrdev, id="directory_widget")
        self.model_list = ModelSelectionWidget(id="model_list")
        self.task_count = 0
        self.button_container = ButtonContainer(id="button_container")
        self.chat_list = ChatList(self.jrdev, id="chat_list")
        self.chat_view = ChatViewWidget(self.jrdev, id="chat_view")
        
        # Initialize content switcher
        self.content_switcher = BorderedSwitcher(id="content_switcher", initial="terminal_output_container")

        with Horizontal():
            with self.vlayout_left:
                yield self.button_container
                yield self.chat_list
            with self.vlayout_terminal:
                yield self.task_monitor
                with self.content_switcher:
                    yield self.terminal_output_widget
                    yield self.chat_view
            with self.vlayout_right:
                yield self.directory_widget
                yield self.model_list

    async def on_mount(self) -> None:
        # init state of project context for chat widget
        self.chat_view.set_project_context_on(self.jrdev.state.use_project_context)

        self._setup_styles()

        # init jrdev core and setup AI models
        await self.jrdev.initialize_services()
        await self._setup_models()

        await self.init_chat_list()

        # Final setup
        self.jrdev.setup_complete()
        self.print_welcome()

    def print_welcome(self) -> None:
        """Print startup messages"""
        # More welcoming and includes a tagline
        self.terminal_output_widget.append_text(f"Welcome to JrDev Terminal v{__version__}!\n")
        self.terminal_output_widget.append_text("Chat, Code, Review—All from Your Shell\n\n")

        # Structured guidance for key actions
        self.terminal_output_widget.append_text("Get Started:\n")
        self.terminal_output_widget.append_text("  - New Chat: Click \"+ New Chat\" (left panel) to talk to the AI.\n")
        self.terminal_output_widget.append_text("  - Coding Tasks: Use /code [your task description] in this terminal.\n")
        self.terminal_output_widget.append_text("  - All Commands: Type /help for a full list.\n\n")

        # Tip for discovering other UI features
        self.terminal_output_widget.append_text("Explore: Use the right panels to manage Project Files & AI Models.\n\n")

        # Clear exit instructions
        self.terminal_output_widget.append_text("Quit: Type /exit or press Ctrl+Q.\n\n")

    async def init_chat_list(self) -> None:
        """Add all chat threads to chat list widget, mark current thread"""
        message_threads = self.jrdev.get_all_threads()
        for thr in message_threads:
            await self.chat_list.add_thread(thr)
        current_thread = self.jrdev.get_current_thread()
        self.chat_list.set_active(current_thread.thread_id)

    async def _setup_models(self) -> None:
        """Initialize the models in the core app"""
        models = self.jrdev.get_models()

        # Set up the model list widget with the models
        await self.model_list.setup_models(models)

        # Set the current model as selected if available
        if self.jrdev.state.model:
            self.model_list.set_model_selected(self.jrdev.state.model)

        self.model_list.styles.height = "50%"  # Relative to parent vlayout_right

    def _setup_styles(self) -> None:
        # directory widget styling
        self.directory_widget.border_title = "Project Files"
        self.directory_widget.styles.border = ("round", Color.parse("#5e5e5e"))
        self.directory_widget.styles.border_title_color = "#fabd2f"
        self.directory_widget.styles.height = "50%"
        self.directory_widget.update_highlights()

        self.button_container.border_title = "Settings"
        self.button_container.styles.border = ("round", Color.parse("#5e5e5e"))
        self.button_container.styles.border_title_color = "#fabd2f"
        self.chat_list.border_title = "Chats"
        self.chat_list.styles.border = ("round", Color.parse("#5e5e5e"))
        self.chat_list.styles.border_title_color = "#fabd2f"

        # Horizontal Layout Splits
        self.vlayout_terminal.styles.width = "60%"
        self.vlayout_terminal.styles.height = "1fr"
        self.vlayout_left.styles.width = "15%"

        # Apply height styling to the TaskMonitor container widget
        self.task_monitor.styles.height = "25%"

    @on(CommandTextArea.Submitted, "#cmd_input")
    async def accept_input(self, event: CommandTextArea.Submitted) -> None:
        text = event.value
        # mirror user input to text area
        self.terminal_output_widget.append_text(f"[PrintType=USER]\n>{text}\n\n")

        # is this something that should be tracked as an active task?
        task_id = None
        if self.task_monitor.should_track(text):
            task_id = self.get_new_task_id()

        # pass input to jrdev core
        worker = self.run_worker(self.jrdev.process_input(text, task_id))
        if task_id:
            worker.name = task_id
            self.task_monitor.add_task(task_id, text, "")

        # clear input widget
        self.terminal_output_widget.clear_input()

    @on(CommandTextArea.Submitted, "#chat_input")
    async def accept_chat_input(self, event: CommandTextArea.Submitted) -> None:
        text = event.value

        # show user chat
        await self.chat_view.add_user_message(text)

        # always track chat tasks
        task_id = self.get_new_task_id()

        # Pass input to jrdev core for processing in a background worker
        # The process_input method now handles adding the user message to the thread
        # and initiating the streaming response.
        worker = self.run_worker(self.jrdev.process_chat_input(text, task_id))
        if task_id:
            self.chat_tasks.add(task_id)
            worker.name = task_id
            self.task_monitor.add_task(task_id, text, "") # Add to task monitor if tracked

        # Clear the chat input widget after submission
        self.chat_view.input_widget.clear()

    @on(CommandRequest)
    async def run_command(self, event: CommandRequest) -> None:
        """Pass a command to the core app through a worker"""
        worker = self.run_worker(self.jrdev.process_input(event.command))

    def get_new_task_id(self) -> str:
        id = self.task_count
        self.task_count += 1
        return str(id)

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        worker = event.worker
        state = event.state
        self.task_monitor.worker_updated(worker, state)

    @on(TextualEvents.PrintMessage)
    def handle_print_message(self, event: TextualEvents.PrintMessage) -> None:
        type_string = printtype_to_string(event.print_type)
        if isinstance(event.text, list):
            self.terminal_output_widget.append_text("\n".join(event.text) + "\n")
        else:
            self.terminal_output_widget.append_text(f"[PrintType={type_string}]" + event.text + "\n")

    @on(TextualEvents.StreamChunk)
    async def handle_stream_chunk(self, event: TextualEvents.StreamChunk) -> None:
        """Append incoming LLM stream chunks to the chat output if active thread matches."""
        await self.chat_view.handle_stream_chunk(event)

    @on(TextualEvents.ConfirmationRequest)
    def handle_confirmation_request(self, message: TextualEvents.ConfirmationRequest) -> None:
        """Handle a request for code confirmation from the backend"""
        screen = CodeConfirmationScreen(message.prompt_text, message.diff_lines, message.error_msg)

        # Store the future so we can set the result when the screen is dismissed
        screen.future = message.future

        # When the screen is dismissed, the on_screen_resume will be called with the result
        self.push_screen(screen)

    @on(TextualEvents.StepsRequest)
    def handle_steps_request(self, message: TextualEvents.StepsRequest) -> None:
        screen = StepsScreen(message.steps)
        screen.future = message.future
        self.push_screen(screen)

    @on(TextualEvents.TextEditRequest)
    def handle_text_edit_request(self, message: TextualEvents.TextEditRequest) -> None:
        """Handle a request to show the text editor screen."""
        screen = CodeEditScreen(
            content_lines=message.content_to_edit,
            prompt_message=message.prompt_message,
            future=message.future
        )
        self.push_screen(screen)

    @on(TextualEvents.DeletionRequest)
    def handle_deletion_request(self, message: TextualEvents.DeletionRequest) -> None:
        """Handle a request for file deletion confirmation"""
        screen = FileDeletionScreen(message.filepath)
        screen.future = message.future
        self.push_screen(screen)

    @on(TextualEvents.EnterApiKeys)
    def handle_enter_api_keys(self, message: TextualEvents.EnterApiKeys) -> None:
        def check_keys(keys: dict):
            self.jrdev.save_keys(keys)
            if self.jrdev.state.need_first_time_setup:
                # finish initialization now that keys are setup
                self.run_worker(self.jrdev.initialize_services())

        providers = self.jrdev.provider_list()
        self.push_screen(ApiKeyEntry(core_app=self.jrdev, providers=providers), check_keys)

    @on(Button.Pressed, "#stop-button")
    def handle_stop_button(self) -> None:
        self.workers.cancel_all()

    @on(Button.Pressed, "#button_profiles")
    def handle_profiles_pressed(self) -> None:
        """Open the model profile management screen"""
        self.app.push_screen(ModelProfileScreen(self.jrdev))

    @on(TextualEvents.ModelChanged)
    def handle_model_change(self, message: TextualEvents.ModelChanged) -> None:
        self.model_list.set_model_selected(message.text)

    @on(RadioSet.Changed, "#model_list")
    def handle_model_selected(self, event: RadioSet.Changed) -> None:
        self.jrdev.set_model(str(event.pressed.label), send_to_ui=False)

    @on(TextualEvents.ModelListUpdated)
    async def handle_model_list_updated(self) -> None:
        models = self.jrdev.get_models()
        await self.model_list.update_models(models)

    @on(TextualEvents.ChatThreadUpdate)
    async def handle_chat_update(self, message: TextualEvents.ChatThreadUpdate) -> None:
        """a chat thread has been updated, notify the directory widget to check for context changes"""
        self.directory_widget.reload_highlights()
        # get the thread
        msg_thread = self.jrdev.get_current_thread()
        if msg_thread:
            # update chat_list buttons
            await self.chat_list.thread_update(msg_thread)
            self.chat_list.set_active(msg_thread.thread_id)

            # double check that no threads were deleted
            all_threads = self.jrdev.state.get_thread_ids()
            self.chat_list.check_threads(all_threads)

            # update chat view
            await self.chat_view.on_thread_switched()

    @on(TextualEvents.CodeContextUpdate)
    def handle_code_context_update(self, message: TextualEvents.CodeContextUpdate) -> None:
        """The staged code context has been updated, notify directory widget to check for context changes"""
        self.directory_widget.reload_highlights()

    @on(TextualEvents.ProjectContextUpdate)
    def handle_project_context_update(self, event: TextualEvents.ProjectContextUpdate) -> None:
        """Project context has been turned on or off"""
        self.chat_view.handle_external_update(event.is_enabled)

    @on(TextualEvents.TaskUpdate)
    def handle_task_update(self, message: TextualEvents.TaskUpdate) -> None:
        """An update to a task/worker is being sent from the core app"""
        if message.worker_id in self.chat_tasks:
            # check for chat error
            if "error" in message.update:
                # notify user of error
                self.notify(f"Chat message failed. Error: {message.update.get('error')}", severity="error")
        self.task_monitor.handle_task_update(message)

    @on(TextualEvents.ExitRequest)
    def handle_exit_request(self, message: TextualEvents.ExitRequest) -> None:
        """Handle a request to exit the application"""
        self.exit()

    # Add Settings button handler
    @on(Button.Pressed, "#button_settings")
    def handle_settings_pressed(self) -> None:
        """Open the SettingsScreen with Providers tab active by default."""
        if not self.settings_screen:
            self.settings_screen = SettingsScreen(core_app=self.jrdev)
            self.settings_screen.active_view = "providers"
            self.app.push_screen(screen=self.settings_screen, callback=self.handle_settings_screen_closed)

    def handle_settings_screen_closed(self, success: bool) -> None:
        """Called when SettingsScreen is dismissed; clear the reference."""
        self.settings_screen = None

    @on(TextualEvents.ProvidersUpdate)
    async def handle_providers_update(self) -> None:
        if self.settings_screen:
            await self.settings_screen.providers_widget.handle_providers_updated()

    @on(TextualEvents.ModelListUpdated)
    async def handle_models_update(self) -> None:
        if self.settings_screen:
            await self.settings_screen.models_widget.handle_models_updated()

    @on(ChatViewWidget.ShowTerminal)
    def handle_show_terminal(self) -> None:
        """Switch to terminal view"""
        self.content_switcher.current = "terminal_output_container"

    @on(Button.Pressed, ".sidebar_button")
    async def handle_chat_thread_button(self, event: Button.Pressed) -> None:
        """Handle clicks on chat thread buttons in the sidebar"""
        btn = event.button
        
        # If it's the new thread button, let the existing handler manage it
        if btn.id == "new_thread":
            return
            
        # If it's a thread button, switch to chat view
        if btn.id in self.chat_list.buttons:
            # Switch to chat view mode
            self.content_switcher.current = "chat_view"

    @on(ChatList.NewChatActivated)
    async def handle_new_chat_activated(self, event: ChatList.NewChatActivated) -> None:
        """When a new chat is created and activated, switch to chat view and display the new chat."""
        self.content_switcher.current = "chat_view"
        await self.chat_view.on_thread_switched()

    def _on_panel_switched(self, old: str|None, new: str|None) -> None:
        """
        Called whenever the ContentSwitcher flips panels.
        We reset the border_title on the visible view.
        """
        if new == "terminal_output_container":
            # your terminal pane lives in self.terminal_output_widget.layout_output
            self.terminal_output_widget.layout_output.border_title = "JrDev Terminal"
            self.task_monitor.styles.height = "25%"
        elif new == "chat_view":
            # your chat pane lives in self.chat_view.layout_output
            self.chat_view.layout_output.border_title = "Chat"
            self.task_monitor.styles.height = 6 # min size to display a row


def run_textual_ui() -> None:
    """Entry point for textual UI console script"""
    JrDevUI().run()


if __name__ == "__main__":
    run_textual_ui()
