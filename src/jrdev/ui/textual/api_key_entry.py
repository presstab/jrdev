from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Input
import logging
logger = logging.getLogger("jrdev")


class ApiKeyEntry(Screen[dict]):
    """Modal Dialog To Enter Api Keys"""
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Enter API Keys")
            with Horizontal():
                yield Label("Venice Key:")
                yield Input(id="venice_key")
            with Horizontal():
                yield Label("OpenAi Key:")
                yield Input(id="openai_key")
            with Horizontal():
                yield Label("Anthropic Key:")
                yield Input(id="anthropic_key")
            with Horizontal():
                yield Label("DeepSeek Key:")
                yield Input(id="deepseek_key")
            with Horizontal():
                yield Button("Save", id="save")
                yield Button("Exit", id="exit")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            venice_key = self.query_one("#venice_key", Input).value
            if not venice_key:
                #todo toast that says required
                self.notify("Must Enter An Api Key For Venice", severity="warning")
                return

            ret = {}
            ret["VENICE_API_KEY"] = venice_key
            openai_key = self.query_one("#openai_key", Input).value
            anthropic_key = self.query_one("#anthropic_key", Input).value
            deepseek_key = self.query_one("#deepseek_key", Input).value

            if openai_key:
                ret["OPENAI_API_KEY"] = openai_key
            if anthropic_key:
                ret["ANTHROPIC_API_KEY"] = anthropic_key
            if deepseek_key:
                ret["DEEPSEEK_API_KEY"] = deepseek_key

            self.dismiss(ret)
        else:
            # exit button pushed
            self.exit()
