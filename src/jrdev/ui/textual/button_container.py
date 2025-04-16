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
    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.api_keys_button = Button("API Keys", id="button_api_keys")

    def compose(self) -> ComposeResult:
        yield self.api_keys_button

    async def on_mount(self) -> None:
        self.can_focus = False
        self.api_keys_button.can_focus = False
        self.api_keys_button.styles.border = "none"
        self.api_keys_button.styles.min_width = 4
        self.api_keys_button.styles.width = "100%"
        self.api_keys_button.styles.align_horizontal = "center"