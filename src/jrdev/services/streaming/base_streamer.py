from abc import ABC, abstractmethod
import time
from typing import Any, AsyncIterator, Dict, List

import tiktoken

from jrdev.core.usage import get_instance


class BaseStreamer(ABC):
    """Abstract base class for LLM provider streamers."""

    def __init__(self, app: Any):
        self.app = app
        self.logger = app.logger
        self.token_encoder = tiktoken.get_encoding("cl100k_base")
        self.log_interval = 100
        self.ui_update_interval = 10

    def _estimate_input_tokens(self, messages: List[Dict[str, Any]], system_message: str = None) -> int:
        """Estimates the number of input tokens for a list of messages."""
        content = ""
        for msg in messages:
            if isinstance(msg.get("content"), str):
                content += msg["content"]
            elif isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        content += item.get("text", "")
        if system_message:
            content += system_message
        return len(self.token_encoder.encode(content))

    def _update_ui_initial(self, task_id: str, model: str, messages: List[Dict[str, Any]], system_message: str = None):
        """Updates the UI with initial token estimates."""
        if not task_id:
            return
        try:
            input_token_estimate = self._estimate_input_tokens(messages, system_message)
            self.app.ui.update_task_info(task_id, update={"input_token_estimate": input_token_estimate, "model": model})
        except Exception as e:
            self.logger.error(f"Error estimating input tokens: {e}")

    def _log_chunk_progress(self, chunk_count: int, model: str, stream_start_time: float):
        """Logs the progress of receiving chunks from the stream."""
        if chunk_count > 0 and stream_start_time and chunk_count % self.log_interval == 0:
            elapsed = time.time() - stream_start_time
            chunks_per_sec = round(chunk_count / elapsed, 2) if elapsed > 0 else 0
            self.logger.info(f"Received {chunk_count} chunks from {model} ({chunks_per_sec} chunks/sec)")

    def _update_ui_streaming(self, task_id: str, chunk_text: str, chunk_count: int, output_tokens_estimate: int, stream_start_time: float) -> int:
        """Updates the UI with streaming progress (token count, TPS)."""
        if not task_id or not stream_start_time:
            return output_tokens_estimate
        try:
            tokens = self.token_encoder.encode(chunk_text)
            output_tokens_estimate += len(tokens)
            if chunk_count > 0 and chunk_count % self.ui_update_interval == 0:
                elapsed = time.time() - stream_start_time
                tps = (output_tokens_estimate / elapsed) if elapsed > 0 else 0
                self.app.ui.update_task_info(
                    worker_id=task_id,
                    update={"output_token_estimate": output_tokens_estimate, "tokens_per_second": tps}
                )
        except Exception as e:
            self.logger.error(f"Error estimating output tokens for chunk: {e}")
        return output_tokens_estimate

    async def _finalize_stream(
        self,
        task_id: str,
        model: str,
        chunk_count: int,
        start_time: float,
        stream_start_time: float,
        input_tokens: int,
        output_tokens: int,
        output_token_estimate: int
    ):
        """Finalizes the stream, logging stats and updating usage."""
        if not stream_start_time: # Stream never started, probably an error before that
            self.logger.warning(f"Stream for {model} did not start. Finalization skipped.")
            return

        end_time = time.time()
        elapsed_seconds = round(end_time - start_time, 2)
        stream_elapsed = end_time - stream_start_time
        chunks_per_sec = round(chunk_count / stream_elapsed, 2) if stream_elapsed > 0 else 0

        final_output_tokens = output_tokens if output_tokens > 0 else output_token_estimate
        
        if output_tokens > 0:
            log_output_tokens_str = str(output_tokens)
        else:
            log_output_tokens_str = f"N/A (estimated {output_token_estimate})"

        self.logger.info(
            f"Response completed: {model}, {input_tokens} input tokens, "
            f"{log_output_tokens_str} output tokens, {elapsed_seconds}s, "
            f"{chunk_count} chunks, {chunks_per_sec} chunks/sec"
        )

        if output_tokens > 0:
            await get_instance().add_use(model, input_tokens, output_tokens)

        if task_id:
            tps = round(final_output_tokens / stream_elapsed, 2) if stream_elapsed > 0 else 0
            self.app.ui.update_task_info(
                worker_id=task_id,
                update={
                    "input_tokens": input_tokens,
                    "output_tokens": final_output_tokens,
                    "tokens_per_second": tps
                }
            )

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
