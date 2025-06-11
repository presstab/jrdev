from textual import events, on
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button
from typing import Dict, Optional
import logging

# Import the new screen
from jrdev.ui.tui.git_tools_screen import GitToolsScreen

logger = logging.getLogger("jrdev")

class ButtonContainer(Widget):
    BUTTONS = [
        {"label": "Profiles", "id": "button_profiles"},
        {"label": "Git Tools", "id": "git"},
        {"label": "Settings", "id": "button_settings"},
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

    @on(Button.Pressed, "#git")
    def handle_git_tools_pressed(self, event: Button.Pressed) -> None:
        """Handle the Git Tools button press by opening the GitToolsScreen."""
        # Access the core application instance via self.app.jrdev
        self.app.push_screen(GitToolsScreen(core_app=self.app.jrdev))
