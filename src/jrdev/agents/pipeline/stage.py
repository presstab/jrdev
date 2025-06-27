import abc
from typing import Any, Dict


class Stage(abc.ABC):
    """
    A single pipeline stage.  Each stage gets the same `ctx` dict,
    can pull inputs from it and write outputs back into it.
    """

    def __init__(self, agent: Any):
        # Give every stage access to the CodeAgent instance
        self.agent = agent
        self.app = agent.app

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        A human‐friendly name for logging / debugging.
        """
        ...

    @abc.abstractmethod
    async def run(self, ctx: Dict[str, Any]) -> None:
        """
        Perform this stage’s work, reading from and writing to ctx.
        Must not return anything.
        """
        ...
