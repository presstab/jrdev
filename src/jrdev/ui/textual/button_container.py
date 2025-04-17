from textual import events, on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.document._document import Selection
from textual.geometry import Size
from textual.widget import Widget
from textual.widgets import Button
from textual.color import Color
from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("jrdev")

class ButtonContainer(Widget):
    BUTTONS = [
        {"label": "API Keys", "id": "button_api_keys"},
        {"label": "Agents", "id": "agents"},
        {"label": "Git Tools", "id": "git"},
    ]

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.buttons: Dict[str, Button] = {}
        for btn in self.BUTTONS:
            button = Button(btn["label"], id=btn["id"], classes="sidebar_button")
            self.buttons[btn["id"]] = button

    def compose(self) -> ComposeResult:
        for button in self.buttons.values():
            yield button

    async def on_mount(self) -> None:
        self.can_focus = False
        for button in self.buttons.values():
            button.can_focus = False
            button.styles.border = "none"
            button.styles.min_width = 4
            button.styles.width = "100%"
            button.styles.align_horizontal = "center"
