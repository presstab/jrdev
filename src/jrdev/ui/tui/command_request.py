from textual.message import Message

class CommandRequest(Message):
    """Sent by any child who wants JrDevUI to run a command."""
    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command