from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Input, Static
from textual.css.query import NoMatches
import logging
logger = logging.getLogger("jrdev")


class ApiKeyEntry(Screen[dict]):
    """Modal Dialog To Enter Api Keys"""
    CSS = """
    Vertical {
        margin: 0;
        padding: 0 4;
        height: auto;
    }

    Horizontal {
        margin: 0 0 1 0;
        padding: 0;
        height: auto;
    }

    Label {
        margin: 0;
        padding: 0;
        width: 16;
    }

    Input {
        margin: 0;
        padding: 0;
        height: 1;
        border: none;
    }
    
    Button {
        margin: 2
    }
    
    #title {
        text-align: center;
        margin-bottom: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Enter API Keys", id="title")
            h1 = Horizontal()
            i1 = Input(id="venice_key")
            with h1:
                yield Label("Venice Key:")
                yield i1
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
            spacer = Static()
            spacer.styles.height = "1fr"
            yield spacer


    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            venice_key = self.query_one("#venice_key", Input).value
            if not venice_key:
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
