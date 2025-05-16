import copy

from textual import on
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, RadioSet, TextArea
from textual.worker import Worker, WorkerState
from textual.color import Color
from typing import Any, Generator
import logging
from jrdev.core.application import Application
from jrdev.ui.textual_events import TextualEvents
from jrdev.ui.textual.code_confirmation_screen import CodeConfirmationScreen
from jrdev.ui.textual.steps_screen import StepsScreen
from jrdev.ui.textual.filtered_directory_tree import DirectoryWidget, FilteredDirectoryTree
from jrdev.ui.textual.api_key_entry import ApiKeyEntry
from jrdev.ui.textual.model_selection_widget import ModelSelectionWidget
from jrdev.ui.textual.task_monitor import TaskMonitor
from jrdev.ui.textual.terminal_output_widget import TerminalOutputWidget
from jrdev.ui.textual.input_widget import CommandTextArea
from jrdev.ui.textual.button_container import ButtonContainer
from jrdev.ui.textual.chat_list import ChatList
from jrdev.ui.textual.model_profile_widget import ModelProfileScreen
from jrdev.ui.textual.command_request import CommandRequest
from jrdev.ui.textual.chat_view_widget import ChatViewWidget
from jrdev.ui.textual.chat_input_widget import ChatInputWidget
from jrdev.ui.textual.bordered_switcher import BorderedSwitcher

logger = logging.getLogger("jrdev")

class JrDevUI(App[None]):
    CSS = """
        Screen {
            background: #1e1e1e;
        }
        Button {
            background: #2a2a2a;
            border: none;
            text-style: none;
            color: #63f554;
            text-align: center;
            height: 1;
            padding: 0 0 0 0;
        }
        Button:hover {
            background: #656565;
            border: none;
        }
        #copy_button:hover {
            background: #656565;
            border: none;
        }
        .sidebar_button {
            background: #2a2a2a;
            border: none;
            text-style: none;
            color: #63f554;
            text-align: center;
            height: 1;
            padding: 0 0 0 0;
        }
        .sidebar_button:hover {
            background: #656565;
            border: none;
        }
        .sidebar_button.active {
            color:  #27dfd0;
            background: #2a2a2a;
            border: none;
            text-style: none;
            text-align: center;
            height: 1;
            padding: 0 0 0 0;
        }
        .sidebar_button.active:hover {
            background: #656565;
            border: none;
        }
        RadioSet {
            border: tall $border-blurred;
            background: #1e1e1e;
            border-title-background: #1e1e1e;
            padding: 0;
            height: auto;
            width: auto;
    
            & > RadioButton {
                background: #1e1e1e;
                border: none;
                padding: 0 0 0 0;
    
                & > .toggle--button {
                    color: #444444;
                    background: #1e1e1e;
                    border: none;
                    padding: 0 0;
                }
    
                &.-selected {
                    background: #1e1e1e;
                    border: none;
                }
            }
    
            & > RadioButton.-on .toggle--button {
                color: #63f554;
                background: #1e1e1e;
                border: none;
            }
    
            &:focus {
                /* The following rules/styles mimic similar ToggleButton:focus rules in
                * ToggleButton. If those styles ever get updated, these should be too.
                */
                border: none;
                background-tint: #1e1e1e;
                & > RadioButton.-selected {
                    color: #1e1e1e;
                    text-style: $block-cursor-text-style;
                    background: #1e1e1e;
                }
            }
        }

        /* Apply consistent scrollbar styling */
        TaskMonitor, ModelSelectionWidget, #diff-display, TerminalTextArea, #cmd_input, DirectoryTree, VerticalScroll {
            scrollbar-background: #1e1e1e;
            scrollbar-background-hover: #1e1e1e;
            scrollbar-background-active: #1e1e1e;
            scrollbar-color: #63f554 30%;
            scrollbar-color-active: #63f554;
            scrollbar-color-hover: #63f554 50%;
        }
        /* Make the container widget flexible */
        TerminalOutputWidget {
            height: 100%;
            background: #1e1e1e;
            border-title-background: #1e1e1e;
        }
        /* Make the inner text area fill its parent and remove border */
        #terminal_output {
             height: 1fr;
             border: none;
             background: #1e1e1e;
             border-title-background: #1e1e1e;
        }
        /* Style the copy button */
        #copy_button {
            height: 1;
            margin-top: 0;
            dock: bottom;
            background: #2a2a2a;
        }
        
        #add_chat_context_button, #add_code_context_button {
            min-width: 3;
        }
        
        ContentSwitcher {
            height: 1fr;
        }
        
        /* Ensure consistent background for all containers and widgets */
        Vertical, Horizontal, DirectoryWidget, FilteredDirectoryTree, TaskMonitor, 
        ModelSelectionWidget, ButtonContainer, DirectoryTree {
            background: #1e1e1e;
            border-title-background: #1e1e1e;
        }
        
        /* Ensure consistent background for directory widget components */
        #directory_widget_container, #directory_widget_buttons {
            background: #1e1e1e;
            border-title-background: #1e1e1e;
        }
        
        /* Ensure all widgets with borders have matching border backgrounds */
        #task_monitor, #cmd_input, #model_list, #directory_widget, #button_container, #chat_list {
            border-title-background: #1e1e1e;
        }
        
        #button_container, #chat_list {
            height: auto;
        }
        
        Horizontal {
            layout: horizontal;
        }
        
        #chat_view {
            height: 1fr;
            width: 100%;
        }
    """
    def compose(self) -> Generator[Any, None, None]:
        # todo welcome message
        self.jrdev = Application()
        self.jrdev.ui = TextualEvents(self)
        self.title = "JrDev Terminal"
        self.jrdev.setup()
        self.vlayout_terminal = Vertical()
        self.vlayout_right = Vertical()
        self.vlayout_left = Vertical()
        # Give the widget an ID for easier CSS targeting
        self.terminal_output_widget = TerminalOutputWidget(id="terminal_output_container")
        self.task_monitor = TaskMonitor() # This is now the container widget
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

        # directory widget styling
        self.directory_widget.border_title = "Project Files"
        self.directory_widget.styles.border = ("round", Color.parse("#63f554"))
        self.directory_widget.styles.height = "50%"
        self.directory_widget.update_highlights()

        self.button_container.border_title = "Settings"
        self.button_container.styles.border = ("round", Color.parse("#63f554"))
        self.chat_list.border_title = "Chats"
        self.chat_list.styles.border = ("round", Color.parse("#63f554"))

        # Horizontal Layout Splits
        self.vlayout_terminal.styles.width = "60%"
        self.vlayout_terminal.styles.height = "1fr"
        self.vlayout_left.styles.width = "15%"

        # --- Vertical Layout Splits within vlayout_terminal ---
        # Apply height styling to the TaskMonitor container widget
        self.task_monitor.styles.height = "25%" # Fixed percentage

        await self.jrdev.initialize_services()

        models = self.jrdev.get_models()

        # Set up the model list widget with the models
        await self.model_list.setup_models(models)

        # Set the current model as selected if available
        if self.jrdev.state.model:
            self.model_list.set_model_selected(self.jrdev.state.model)

        self.model_list.styles.height = "50%" # Relative to parent vlayout_right

        # add current thread to chat list
        current_thread = self.jrdev.get_current_thread()
        await self.chat_list.add_thread(current_thread)
        self.jrdev.setup_complete()

    @on(CommandTextArea.Submitted, "#cmd_input")
    async def accept_input(self, event: CommandTextArea.Submitted) -> None:
        text = event.value
        # mirror user input to text area
        self.terminal_output_widget.append_text(f"> {text}\n")

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
        worker = self.run_worker(self.jrdev.process_input(text, task_id))
        if task_id:
            worker.name = task_id
            self.task_monitor.add_task(task_id, text, "") # Add to task monitor if tracked

        # Clear the chat input widget after submission
        self.chat_view.input_widget.clear()

    @on(CommandRequest)
    async def run_command(self, event: CommandRequest) -> None:
        """Pass a command to the core app through a worker"""
        worker = self.run_worker(self.jrdev.process_input(event.command))

    def get_new_task_id(self):
        id = self.task_count
        self.task_count += 1
        return str(id)

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        worker = event.worker
        state = event.state
        self.task_monitor.worker_updated(worker, state)

    @on(TextualEvents.PrintMessage)
    def handle_print_message(self, event: Any) -> None:
        if isinstance(event.text, list):
            self.terminal_output_widget.append_text("\n".join(event.text) + "\n")
        else:
            self.terminal_output_widget.append_text(event.text + "\n")

    @on(TextualEvents.StreamChunk)
    async def handle_stream_chunk(self, event: TextualEvents.StreamChunk) -> None:
        """Append incoming LLM stream chunks to the chat output if active thread matches."""
        await self.chat_view.handle_stream_chunk(event)

    @on(TextualEvents.ConfirmationRequest)
    def handle_confirmation_request(self, message: TextualEvents.ConfirmationRequest) -> None:
        """Handle a request for code confirmation from the backend"""
        screen = CodeConfirmationScreen(message.prompt_text, message.diff_lines)

        # Store the future so we can set the result when the screen is dismissed
        screen.future = message.future

        # When the screen is dismissed, the on_screen_resume will be called with the result
        self.push_screen(screen)

    @on(TextualEvents.StepsRequest)
    def handle_steps_request(self, message: TextualEvents.StepsRequest):
        screen = StepsScreen(message.steps)
        screen.future = message.future
        self.push_screen(screen)

    @on(TextualEvents.EnterApiKeys)
    def handle_enter_api_keys(self, message: TextualEvents.EnterApiKeys):
        def check_keys(keys: dict):
            self.jrdev.save_keys(keys)
            if self.jrdev.state.need_first_time_setup:
                # finish initialization now that keys are setup
                self.run_worker(self.jrdev.initialize_services())

        providers = self.jrdev.provider_list()
        self.push_screen(ApiKeyEntry(core_app=self.jrdev, providers=providers), check_keys)

    @on(Button.Pressed, "#button_api_keys")
    def handle_edit_api_keys(self):
        def save_keys(keys: dict):
            self.jrdev.save_keys(keys)
            self.run_worker(self.jrdev.reload_api_clients())

        providers = self.jrdev.provider_list()
        self.push_screen(ApiKeyEntry(core_app=self.jrdev, providers=providers, mode="editor"), save_keys)

    @on(Button.Pressed, "#stop-button")
    def handle_stop_button(self):
        self.workers.cancel_all()

    @on(Button.Pressed, "#button_profiles")
    def handle_profiles_pressed(self):
        """Open the model profile management screen"""
        self.app.push_screen(ModelProfileScreen(self.jrdev))

    @on(TextualEvents.ModelChanged)
    def handle_model_change(self, message: TextualEvents.ModelChanged):
        self.model_list.set_model_selected(message.text)

    @on(RadioSet.Changed, "#model_list")
    def handle_model_selected(self, event: RadioSet.Changed):
        self.jrdev.set_model(str(event.pressed.label), send_to_ui=False)

    @on(TextualEvents.ChatThreadUpdate)
    async def handle_chat_update(self, message: TextualEvents.ChatThreadUpdate):
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
    def handle_code_context_update(self, message: TextualEvents.CodeContextUpdate):
        """The staged code context has been updated, notify directory widget to check for context changes"""
        self.directory_widget.reload_highlights()

    @on(TextualEvents.ProjectContextUpdate)
    def handle_project_context_update(self, event: TextualEvents.ProjectContextUpdate):
        """Project context has been turned on or off"""
        self.chat_view.handle_external_update(event.is_enabled)

    @on(TextualEvents.TaskUpdate)
    def handle_task_update(self, message: TextualEvents.TaskUpdate):
        """An update to a task/worker is being sent from the core app"""
        self.task_monitor.handle_task_update(message)

    @on(TextualEvents.ExitRequest)
    def handle_exit_request(self, message: TextualEvents.ExitRequest) -> None:
        """Handle a request to exit the application"""
        self.exit()

    @on(ChatViewWidget.ShowTerminal)
    def handle_show_terminal(self):
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
