from textual.widgets import Input
from textual.color import Color

class CommandInput(Input):
    def __init__(self, placeholder: str, id: str):
        super().__init__(placeholder="Enter Command", id="cmd_input")
        self.border_title = "Command Input"
        self.styles.border = ("round", Color.parse("#63f554"))