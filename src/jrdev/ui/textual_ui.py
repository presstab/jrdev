from textual import on
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import DirectoryTree, Header, Input, Label, RadioButton, RadioSet, RichLog
from textual.events import Event
from textual.color import Color
from typing import Any, Generator, List, Optional, Tuple
from collections import defaultdict, OrderedDict
import logging
import asyncio
from jrdev.core.application import Application
from jrdev.ui.textual_events import TextualEvents
from jrdev.ui.textual.confirmation_screen import ConfirmationScreen
from jrdev.ui.textual.api_key_entry import ApiKeyEntry

logger = logging.getLogger("jrdev")


class JrDevUI(App[None]):
    CSS = """
        RichLog {
            scrollbar-background: #1e1e1e;
            scrollbar-background-hover: #1e1e1e;
            scrollbar-background-active: #1e1e1e;
            scrollbar-color: #63f554 30%;
            scrollbar-color-active: #63f554;
            scrollbar-color-hover: #63f554 50%;
        }
        
        RadioSet {
            border: tall $border-blurred;
            background: #1e1e1e;
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
    """
    def compose(self) -> Generator[Any, None, None]:
        # todo welcome message
        self.jrdev = Application()
        self.jrdev.ui = TextualEvents(self)
        self.title = "JrDev Terminal"
        self.jrdev.setup()
        self.vlayout_terminal = Vertical()
        self.vlayout_right = Vertical()
        self.terminal_output = RichLog(id="terminal_output", min_width=10)
        self.terminal_input = Input(placeholder="Enter Command", id="cmd_input")
        #todo active tasks
        self.running_tasks = RichLog()
        #todo filter out jrdev dir
        self.directory_tree = DirectoryTree("./")
        self.model_list = RadioSet()

        with Horizontal():
            with self.vlayout_terminal:
                yield self.running_tasks
                yield self.terminal_output
                yield self.terminal_input
            with self.vlayout_right:
                yield self.directory_tree
                yield self.model_list

    async def on_mount(self) -> None:
        self.running_tasks.border_title = "Running Tasks"
        self.running_tasks.styles.border = ("round", Color.parse("#63f554"))
        self.terminal_output.wrap = True
        self.terminal_output.markup = True
        self.terminal_output.can_focus = False
        self.terminal_output.border_title = "JrDev Terminal"
        self.terminal_output.styles.border = ("round", Color.parse("#63f554"))
        self.terminal_input.focus()
        self.terminal_input.border_title = "Command Input"
        self.terminal_input.styles.border = ("round", Color.parse("#63f554"))
        self.directory_tree.border_title = "Project Files"
        self.directory_tree.styles.border = ("round", Color.parse("#63f554"))
        self.model_list.border_title = "Model"
        self.model_list.styles.border = ("round", Color.parse("#63f554"))
        self.model_list.styles.width = "100%"
        self.model_list.can_focus = False

        # Horizontal Layout Splits
        self.vlayout_terminal.styles.width = "70%"

        # Terminal Layout Splits
        self.running_tasks.styles.height = "25%"

        await self.jrdev.initialize_services()

        models = self.jrdev.get_models()
        models_by_provider = defaultdict(list)

        for model in models:
            logger.info(f"{model}")
            models_by_provider[model["provider"]].append(model)

        # Reorder to put 'venice' first
        ordered_providers = OrderedDict()

        # Add 'venice' group first if it exists
        if "venice" in models_by_provider:
            ordered_providers["venice"] = models_by_provider.pop("venice")

        # Add remaining providers in sorted order (optional)
        for provider in sorted(models_by_provider):
            ordered_providers[provider] = models_by_provider[provider]

        # Mount grouped UI
        for provider, model_group in ordered_providers.items():
            await self.model_list.mount(Label(f"{provider}", classes="provider-label"))
            for model in model_group:
                button = RadioButton(model["name"])
                button.can_focus = False
                button.BUTTON_RIGHT = " "
                button.BUTTON_LEFT = " "
                await self.model_list.mount(button)

    @on(Input.Submitted, "#cmd_input")
    async def accept_input(self, event: Event) -> None:
        text = self.terminal_input.value
        # mirror user input to richlog
        self.terminal_output.write(f"[blue]>[/blue][green]{text}[/green]")
        # pass input to jrdev core
        self.run_worker(self.jrdev.process_input(text))
        self.terminal_input.value = ""

    @on(TextualEvents.PrintMessage)
    def handle_print_message(self, event: Any) -> None:
        self.terminal_output.write(event.text)

    @on(TextualEvents.ConfirmationRequest)
    def handle_confirmation_request(self, message: TextualEvents.ConfirmationRequest) -> None:
        """Handle a request for confirmation from the backend"""
        screen = ConfirmationScreen(message.prompt_text, message.diff_lines)
        
        # Store the future so we can set the result when the screen is dismissed
        screen.future = message.future
        
        # When the screen is dismissed, the on_screen_resume will be called with the result
        self.push_screen(screen)

    @on(TextualEvents.EnterApiKeys)
    def handle_enter_api_keys(self, message: TextualEvents.EnterApiKeys):
        def check_keys(keys: dict):
            self.jrdev.save_keys(keys)
            if self.jrdev.state.need_first_time_setup:
                # finish initialization now that keys are setup
                self.run_worker(self.jrdev.initialize_services())

        self.push_screen(ApiKeyEntry(), check_keys)
        
    @on(TextualEvents.ExitRequest)
    def handle_exit_request(self, message: TextualEvents.ExitRequest) -> None:
        """Handle a request to exit the application"""
        self.exit()


def run_textual_ui() -> None:
    """Entry point for textual UI console script"""
    JrDevUI().run()


if __name__ == "__main__":
    run_textual_ui()