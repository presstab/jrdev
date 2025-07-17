from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List


class BaseStreamer(ABC):
    """Abstract base class for LLM provider streamers."""

    def __init__(self, app: Any):
        self.app = app
        self.logger = app.logger

    @abstractmethod
    async def stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        task_id: str = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Streams a response from the language model.

        Args:
            model: The name of the model to use.
            messages: A list of message dictionaries, OpenAI format.
            task_id: The optional ID of the task for UI updates.
            **kwargs: Additional provider-specific arguments.

        Yields:
            A string chunk of the response.
        """
        # This is an abstract method, so it should not have a real implementation.
        # The `yield` statement is here to make this an async generator function.
        # It will never be executed.
        if False:
            yield
