from dataclasses import dataclass, field
from typing import List


@dataclass
class ToolCall:
    """Represents a tool call to be executed by the system."""
    action_type: str
    command: str
    args: List[str] = field(default_factory=list)
    has_next: bool = True
    reasoning: str = ""
    result: str = ""

    @property
    def formatted_cmd(self) -> str:
        """Generates the full command string from the command and its arguments."""
        return f"{self.command} {' '.join(self.args)}"
