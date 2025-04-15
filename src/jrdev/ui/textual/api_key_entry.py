from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Input, Static
from textual.css.query import NoMatches
import logging
import json
from pathlib import Path
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
    
    def __init__(self, providers):
        super().__init__()
        self.providers = providers
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Enter API Keys", id="title")
            for provider in self.providers:
                with Horizontal():
                    yield Label(f"{provider['name'].title()} Key:")
                    yield Input(id=f"{provider['name']}_key", password=True)
            with Horizontal():
                yield Button("Save", id="save")
                yield Button("Exit", id="exit")
            spacer = Static()
            spacer.styles.height = "1fr"
            yield spacer

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            ret = {}
            for provider in self.providers:
                key = self.query_one(f"#{provider['name']}_key", Input).value
                if provider["required"] and not key:
                    self.notify(f"Must Enter An Api Key For {provider['name'].title()}", severity="warning")
                    return
                if key:
                    ret[provider["env_key"]] = key
            self.dismiss(ret)
        else:
            # exit button pushed
            self.exit()