from textual import on
from textual.app import App
from textual.widgets import Header, Input, RichLog
from textual.events import Event
from typing import Any, Generator, List, Optional, Tuple
import logging
import asyncio
from jrdev.core.application import Application
from jrdev.ui.textual_events import TextualEvents
from jrdev.ui.textual.confirmation_screen import ConfirmationScreen


logger = logging.getLogger("jrdev")


class JrDevUI(App[None]):
    def compose(self) -> Generator[Any, None, None]:
        self.jrdev = Application()
        # Create TextualEvents with reference to self
        self.jrdev.ui = TextualEvents(self)
        self.title = "JrDev Terminal"
        yield Header()
        yield RichLog()
        yield Input(placeholder="Type here").focus()

    async def on_mount(self) -> None:
        self.query_one(RichLog).wrap = True
        self.query_one(RichLog).markup = True

        await self.jrdev.initialize_services()

    @on(Input.Submitted)
    async def accept_input(self, event: Event) -> None:
        input = self.query_one(Input)
        text = input.value
        # Here you would typically pass input to your application logic
        self.run_worker(self.jrdev.process_input(text))
        input.value = ""

    @on(TextualEvents.PrintMessage)
    def handle_print_message(self, event: Any) -> None:
        self.query_one(RichLog).write(event.text)
        
    @on(TextualEvents.ConfirmationRequest)
    def handle_confirmation_request(self, message: TextualEvents.ConfirmationRequest) -> None:
        """Handle a request for confirmation from the backend"""
        screen = ConfirmationScreen(message.prompt_text, message.diff_lines)
        
        # Store the future so we can set the result when the screen is dismissed
        screen.future = message.future
        
        # When the screen is dismissed, the on_screen_resume will be called with the result
        self.push_screen(screen)


def run_textual_ui() -> None:
    """Entry point for textual UI console script"""
    JrDevUI().run()


if __name__ == "__main__":
    run_textual_ui()