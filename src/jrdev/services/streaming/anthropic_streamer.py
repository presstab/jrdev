import time
from typing import Any, AsyncIterator, Dict, List

from jrdev.services.streaming.base_streamer import BaseStreamer


class AnthropicStreamer(BaseStreamer):
    """Streamer for Anthropic API."""

    async def stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        task_id: str = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Streams a response from an Anthropic language model.

        Args:
            model: The name of the model to use.
            messages: A list of message dictionaries in OpenAI format.
            task_id: The optional ID of the task for UI updates.
            **kwargs: Additional arguments (not used for Anthropic).

        Yields:
            A string chunk of the response.
        """
        start_time = time.time()

        # Provider-specific logging
        context_files = []
        for m in messages:
            if isinstance(m.get("content"), str) and "Supporting Context" in m.get("content", ""):
                for line in m["content"].split("\n"):
                    if "Context File" in line and ":" in line:
                        try:
                            context_files.append(line.split(":", 1)[1].strip())
                        except:
                            pass
        log_msg = f"Sending request to {model} with {len(messages)} messages"
        if context_files:
            log_msg += f", context files: {', '.join(context_files)}"
        self.logger.info(log_msg)

        # Provider-specific client setup
        client = self.app.state.clients.anthropic
        if not client:
            raise ValueError(f"Anthropic API key not configured but model {model} requires it")

        # Provider-specific message formatting
        anthropic_messages = []
        system_message = None
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        # Use shared helper for initial UI update
        self._update_ui_initial(task_id, model, messages, system_message)

        try:
            request_kwargs = {"model": model, "messages": anthropic_messages, "max_tokens": 8192, "temperature": 0.0}
            if system_message is not None:
                request_kwargs["system"] = system_message
            
            stream_manager = client.messages.stream(**request_kwargs)

            # Initial setup for streaming
            chunk_count = 0
            output_tokens_estimate = 0
            stream_start_time = None
            final_output_tokens = 0

            async with stream_manager as stream:
                async for chunk in stream:
                    if stream_start_time is None:
                        stream_start_time = time.time()
                        self.logger.info(f"Started receiving response from {model}")

                    chunk_count += 1
                    self._log_chunk_progress(chunk_count, model, stream_start_time)

                    if chunk.type == 'content_block_delta' and hasattr(chunk.delta, 'text'):
                        chunk_text = chunk.delta.text
                        # Use shared helper for streaming UI update
                        output_tokens_estimate = self._update_ui_streaming(
                            task_id, chunk_text, chunk_count, output_tokens_estimate, stream_start_time
                        )
                        yield chunk_text
                    elif chunk.type == 'message_delta' and hasattr(chunk, 'usage') and hasattr(chunk.usage, 'output_tokens'):
                        final_output_tokens += chunk.usage.output_tokens  # Accumulate final output tokens from delta

            # Finalize and log using shared helper
            input_tokens = self._estimate_input_tokens(messages, system_message)
            
            await self._finalize_stream(
                task_id=task_id,
                model=model,
                chunk_count=chunk_count,
                start_time=start_time,
                stream_start_time=stream_start_time,
                input_tokens=input_tokens,
                output_tokens=final_output_tokens,
                output_token_estimate=output_tokens_estimate
            )

        except Exception as e:
            self.logger.error(f"Error making Anthropic API request: {str(e)}")
            raise ValueError(f"Error making Anthropic API request: {str(e)}")
