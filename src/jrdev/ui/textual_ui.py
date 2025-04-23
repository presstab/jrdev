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
from jrdev.ui.textual.model_profile_widget import ModelProfileScreen

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
        TaskMonitor, ModelSelectionWidget, #diff-display, TerminalTextArea, #cmd_input, DirectoryTree {
            scrollbar-background: #1e1e1e;
            scrollbar-background-hover: #1e1e1e;
            scrollbar-background-active: #1e1e1e;
            scrollbar-color: #63f554 30%;
            scrollbar-color-active: #63f554;
            scrollbar-color-hover: #63f554 50%;
        }
        /* Make the container widget flexible */
        TerminalOutputWidget {
            height: 1fr;
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
        #task_monitor, #cmd_input, #model_list, #directory_widget, #button_container {
            border-title-background: #1e1e1e;
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
        self.terminal_input = CommandTextArea(placeholder="Enter Command", id="cmd_input")
        self.task_monitor = TaskMonitor()
        self.directory_widget = DirectoryWidget(core_app=self.jrdev, id="directory_widget")
        self.model_list = ModelSelectionWidget(id="model_list")
        self.task_count = 0
        self.button_container = ButtonContainer()

        with Horizontal():
            with self.vlayout_left:
                yield self.button_container
            with self.vlayout_terminal: # Manages vertical distribution
                yield self.task_monitor
                yield self.terminal_output_widget # Takes flexible space (1fr)
                yield self.terminal_input
            with self.vlayout_right:
                yield self.directory_widget
                yield self.model_list

    async def on_mount(self) -> None:
        self.terminal_output_widget.border_title = "JrDev Terminal"
        self.terminal_output_widget.styles.border = ("round", Color.parse("#63f554"))
        self.terminal_input.focus()
        self.terminal_input.border_title = "Command Input"
        self.terminal_input.styles.border = ("round", Color.parse("#63f554"))

        # directory widget styling
        self.directory_widget.border_title = "Project Files"
        self.directory_widget.styles.border = ("round", Color.parse("#63f554"))
        self.directory_widget.styles.height = "50%"
        self.directory_widget.update_highlights()

        self.button_container.border_title = "Settings"
        self.button_container.styles.border = ("round", Color.parse("#63f554"))

        # Horizontal Layout Splits
        self.vlayout_terminal.styles.width = "65%"
        self.vlayout_left.styles.width = "10%"

        # --- Vertical Layout Splits within vlayout_terminal ---
        self.task_monitor.styles.height = "25%" # Fixed percentage
        self.terminal_input.styles.height = 5   # Fixed rows

        await self.jrdev.initialize_services()

        models = self.jrdev.get_models()

        # Set up the model list widget with the models
        await self.model_list.setup_models(models)

        # Set the current model as selected if available
        if self.jrdev.state.model:
            self.model_list.set_model_selected(self.jrdev.state.model)

        self.model_list.styles.height = "50%" # Relative to parent vlayout_right

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
        self.terminal_input.value = ""

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

    @on(Button.Pressed, "#button_profiles")
    def handle_agents_pressed(self):
        """Open the model profile management screen"""
        self.app.push_screen(ModelProfileScreen(self.jrdev))

    @on(TextualEvents.ModelChanged)
    def handle_model_change(self, message: TextualEvents.ModelChanged):
        self.model_list.set_model_selected(message.text)

    @on(RadioSet.Changed, "#model_list")
    def handle_model_selected(self, event: RadioSet.Changed):
        self.jrdev.set_model(str(event.pressed.label), send_to_ui=False)

    @on(TextualEvents.ChatThreadUpdate)
    def handle_chat_update(self, message: TextualEvents.ChatThreadUpdate):
        """a chat thread has been updated, notify the directory widget to check for context changes"""
        self.directory_widget.reload_highlights()

    @on(TextualEvents.CodeContextUpdate)
    def handle_code_context_update(self, message: TextualEvents.CodeContextUpdate):
        """The staged code context has been updated, notify directory widget to check for context changes"""
        self.directory_widget.reload_highlights()

    @on(TextualEvents.TaskUpdate)
    def handle_task_update(self, message: TextualEvents.TaskUpdate):
        if "input_token_estimate" in message.update:
            # first message gives us input token estimate and model being used
            token_count = message.update["input_token_estimate"]
            model = message.update["model"]
            self.task_monitor.update_input_tokens(message.worker_id, token_count, model)
        elif "output_token_estimate" in message.update:
            token_count = message.update['output_token_estimate']
            tokens_per_second = message.update["tokens_per_second"]
            self.task_monitor.update_output_tokens(message.worker_id, token_count, tokens_per_second)
        elif "input_tokens" in message.update:
            # final official accounting of tokens
            input_tokens = message.update.get("input_tokens")
            self.task_monitor.update_input_tokens(message.worker_id, input_tokens)
            output_tokens = message.update.get("output_tokens")
            tokens_per_second = message.update.get("tokens_per_second")
            self.task_monitor.update_output_tokens(message.worker_id, output_tokens, tokens_per_second)
        elif "new_sub_task" in message.update:
            # new sub task spawned
            sub_task_id = message.update.get("new_sub_task")
            description = message.update.get("description")
            self.task_monitor.add_task(sub_task_id, task_name="init", model="", sub_task_name=description)
        elif "sub_task_finished" in message.update:
            self.task_monitor.set_task_finished(message.worker_id)



    @on(TextualEvents.ExitRequest)
    def handle_exit_request(self, message: TextualEvents.ExitRequest) -> None:
        """Handle a request to exit the application"""
        self.exit()


def run_textual_ui() -> None:
    """Entry point for textual UI console script"""
    JrDevUI().run()


if __name__ == "__main__":
    run_textual_ui()
