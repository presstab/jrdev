import time
import tiktoken
from typing import Any, AsyncIterator, Dict, List

from jrdev.core.usage import get_instance
from jrdev.services.streaming.base_streamer import BaseStreamer


class OpenAIStreamer(BaseStreamer):
    """Streamer for OpenAI-compatible API providers."""

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

        # Start timing the response
        start_time = time.time()

        log_msg = f"Sending request to {model} with {len(messages)} messages"
        self.app.logger.info(log_msg)

        # Get the appropriate client
        model_provider = None

        # Find the model in AVAILABLE_MODELS
        available_models = self.app.get_models()
        for entry in available_models:
            if entry["name"] == model:
                model_provider = entry["provider"]
                break

        # token estimator
        token_encoder = tiktoken.get_encoding("cl100k_base")

        # Select the appropriate client based on provider
        if model_provider not in self.app.state.clients.get_all_clients():
            raise ValueError(f"No client for {model_provider}")
        client = self.app.state.clients.get_client(model_provider)

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

        first_chunk = True
        chunk_count = 0
        log_interval = 100  # Log every 100 chunks
        stream_start_time = None  # Track when we start receiving chunks

        # notify ui of tokens
        if task_id:
            try:
                input_chunk_content = ""
                for msg in messages:
                    if "content" in msg and isinstance(msg["content"], str):
                        input_chunk_content += msg["content"]
                    elif isinstance(msg["content"], list): # Handle list content (e.g. vision models)
                        for item in msg["content"]:
                            if isinstance(item, dict) and item.get("type") == "text":
                                input_chunk_content += item.get("text", "")
                input_token_estimate = token_encoder.encode(input_chunk_content)
                self.app.ui.update_task_info(task_id, update={"input_token_estimate": len(input_token_estimate), "model": model})
            except Exception as e:
                self.app.logger.error(f"Error estimating input tokens: {e}")

        output_tokens_estimate = 0
        final_chunk_data = None
        async for chunk in stream:
            if first_chunk:
                stream_start_time = time.time()
                self.app.logger.info(f"Started receiving response from {model}")
                first_chunk = False
            chunk_count += 1
            if chunk_count % log_interval == 0 and stream_start_time:
                elapsed = time.time() - stream_start_time
                self.app.logger.info(f"Received {chunk_count} chunks from {model} ({round(chunk_count/elapsed,2) if elapsed > 0 else 0} chunks/sec)")

            if chunk.choices and chunk.choices[0].delta.content:
                chunk_text = chunk.choices[0].delta.content
                if task_id:
                    try:
                        tokens = token_encoder.encode(chunk_text)
                        output_tokens_estimate += len(tokens)
                        if chunk_count % 10 == 0 and stream_start_time:
                            elapsed = time.time() - stream_start_time
                            self.app.ui.update_task_info(worker_id=task_id, update={"output_token_estimate": output_tokens_estimate, "tokens_per_second": (output_tokens_estimate)/elapsed if elapsed>0 else 0})
                    except Exception as e:
                        self.app.logger.error(f"Error estimating output tokens for chunk: {e}")
                yield chunk_text
            final_chunk_data = chunk # Store the last chunk to access usage data if available

        if final_chunk_data and hasattr(final_chunk_data, 'usage') and final_chunk_data.usage:
            input_tokens = final_chunk_data.usage.prompt_tokens
            output_tokens = final_chunk_data.usage.completion_tokens
            end_time = time.time()
            elapsed_seconds = round(end_time - start_time, 2)
            stream_elapsed = end_time - (stream_start_time or start_time)
            if task_id:
                self.app.ui.update_task_info(worker_id=task_id, update={"input_tokens": input_tokens, "output_tokens": output_tokens, "tokens_per_second": round(output_tokens/stream_elapsed,2) if stream_elapsed > 0 else 0})
            self.app.logger.info(f"Response completed: {model}, {input_tokens} input tokens, {output_tokens} output tokens, {elapsed_seconds}s, {chunk_count} chunks, {round(chunk_count/stream_elapsed,2) if stream_elapsed > 0 else 0} chunks/sec")
            await get_instance().add_use(model, input_tokens, output_tokens)
        elif stream_start_time: # Fallback if usage not in final chunk but stream happened
            end_time = time.time()
            elapsed_seconds = round(end_time - start_time, 2)
            stream_elapsed = end_time - stream_start_time
            self.app.logger.info(f"Response completed (no usage data in final chunk): {model}, {elapsed_seconds}s, {chunk_count} chunks, {round(chunk_count/stream_elapsed,2) if stream_elapsed > 0 else 0} chunks/sec")
