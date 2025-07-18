import time
from typing import Any, AsyncIterator, Dict, List

from jrdev.services import provider_factory
from jrdev.services.streaming.base_streamer import BaseStreamer


class OpenAIStreamer(BaseStreamer):
    """Streamer for OpenAI-compatible API providers."""

    def __init__(self, logger: Any, ui: Any, usageTracker: Any):
        super().__init__(logger, ui, usageTracker)

    async def stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        task_id: str = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Streams a response from an OpenAI-compatible language model.

        Args:
            model: The name of the model to use.
            messages: A list of message dictionaries in OpenAI format.
            task_id: The optional ID of the task for UI updates.
            **kwargs: Additional arguments. Expected: 'json_output', 'max_output_tokens'.

        Yields:
            A string chunk of the response.
        """
        json_output = kwargs.get("json_output", False)
        max_output_tokens = kwargs.get("max_output_tokens")

        start_time = time.time()

        self.logger.info(f"Sending request to {model} with {len(messages)} messages")

        # Get the appropriate client using the provider factory
        model_provider = provider_factory.get_provider_for_model(model)
        if not model_provider:
            raise ValueError(f"Could not find a provider for model '{model}'")

        client = provider_factory.get_client(model_provider)
        if not client:
            raise ValueError(f"No initialized client found for provider '{model_provider}'")

        # Create a streaming completion
        request_kwargs = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": 0.0,
            "extra_headers": {
                "HTTP-Referer": "https://github.com/presstab/jrdev",
                "X-Title": "JrDev"
            }
        }

        if max_output_tokens:
            request_kwargs["max_completion_tokens"] = max_output_tokens

        if model_provider == "openai":
            if "o3" in model or "o4-mini" in model:
                request_kwargs["reasoning_effort"] = "high"
                del request_kwargs["temperature"]
            request_kwargs["stream_options"] = {"include_usage": True}
        elif model == "qwen-2.5-qwq-32b":
            request_kwargs["top_p"] = 0.95
            request_kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}, "frequency_penalty": 0.3}
        elif model == "deepseek-r1-671b":
            request_kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}}
        elif model == "deepseek-reasoner" or model == "deepseek-chat":
            request_kwargs["max_tokens"] = 8000
            if model == "deepseek-chat" and json_output:
                request_kwargs["response_format"] = {"type": "json_object"}
        elif model_provider == "venice":
            request_kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}}

        stream = await client.chat.completions.create(**request_kwargs)

        # Initial setup for streaming
        chunk_count = 0
        output_tokens_estimate = 0
        stream_start_time = None
        final_chunk_data = None

        self._update_ui_initial(task_id, model, messages)

        async for chunk in stream:
            if stream_start_time is None:
                stream_start_time = time.time()
                self.logger.info(f"Started receiving response from {model}")

            chunk_count += 1
            self._log_chunk_progress(chunk_count, model, stream_start_time)

            if chunk.choices and chunk.choices[0].delta.content:
                chunk_text = chunk.choices[0].delta.content
                output_tokens_estimate = self._update_ui_streaming(
                    task_id, chunk_text, chunk_count, output_tokens_estimate, stream_start_time
                )
                yield chunk_text
            
            final_chunk_data = chunk  # Store the last chunk to access usage data

        # Finalize and log
        input_tokens = 0
        output_tokens = 0
        if final_chunk_data and hasattr(final_chunk_data, 'usage') and final_chunk_data.usage:
            input_tokens = final_chunk_data.usage.prompt_tokens
            output_tokens = final_chunk_data.usage.completion_tokens
        else:
            # Fallback to estimation if usage data is not available
            input_tokens = self._estimate_input_tokens(messages)

        await self._finalize_stream(
            task_id=task_id,
            model=model,
            chunk_count=chunk_count,
            start_time=start_time,
            stream_start_time=stream_start_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            output_token_estimate=output_tokens_estimate
        )