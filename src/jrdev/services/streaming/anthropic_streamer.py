import time
import tiktoken
from typing import Any, AsyncIterator, Dict, List

from jrdev.core.usage import get_instance
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
        self.app.logger.info(log_msg)

        client = self.app.state.clients.anthropic
        if not client:
            raise ValueError(f"Anthropic API key not configured but model {model} requires it")

        anthropic_messages = []
        system_message = None
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        chunk_count = 0
        log_interval = 100
        token_encoder = tiktoken.get_encoding("cl100k_base")
        if task_id:
            try:
                inp_content = ""
                for m in messages:
                    if isinstance(m.get("content"), str):
                        inp_content += m.get("content", "")
                    elif isinstance(m.get("content"), list):
                        for item in m.get("content", []):
                            if isinstance(item, dict) and item.get("type") == "text":
                                inp_content += item.get("text", "")
                self.app.ui.update_task_info(task_id, update={"input_token_estimate": len(token_encoder.encode(inp_content)), "model": model})
            except Exception as e:
                self.app.logger.error(f"Error estimating input tokens for Anthropic: {e}")

        try:
            request_kwargs = {"model": model, "messages": anthropic_messages, "max_tokens": 8192, "temperature": 0.0}
            if system_message is not None:
                request_kwargs["system"] = system_message
            stream_manager = client.messages.stream(**request_kwargs)

            self.app.logger.info(f"Started receiving response from {model}")
            stream_start_time = time.time()
            output_tokens_estimate = 0
            final_output_tokens = 0

            async with stream_manager as stream:
                async for chunk in stream:
                    if chunk.type == 'content_block_delta' and hasattr(chunk.delta, 'text'):
                        ct = chunk.delta.text
                        if task_id:
                            try:
                                tokens = token_encoder.encode(ct)
                                output_tokens_estimate += len(tokens)
                                if chunk_count % 10 == 0 and output_tokens_estimate > 0:
                                    elapsed = time.time() - stream_start_time
                                    self.app.ui.update_task_info(worker_id=task_id, update={"output_token_estimate": output_tokens_estimate, "tokens_per_second": (output_tokens_estimate) / elapsed if elapsed > 0 else 0})
                            except Exception as e:
                                self.app.logger.error(f"Error estimating output tokens for Anthropic chunk: {e}")
                        yield ct
                    elif chunk.type == 'message_delta' and hasattr(chunk, 'usage') and hasattr(chunk.usage, 'output_tokens'):
                        final_output_tokens += chunk.usage.output_tokens  # Accumulate final output tokens from delta

                    chunk_count += 1
                    if chunk_count % log_interval == 0 and stream_start_time:
                        elapsed = time.time() - stream_start_time
                        self.app.logger.info(f"Received {chunk_count} chunks from {model} ({round(chunk_count / elapsed, 2) if elapsed > 0 else 0} chunks/sec)")

            input_tokens_content = ""
            for m in messages:
                if isinstance(m.get("content"), str):
                    input_tokens_content += m.get("content", "")
                elif isinstance(m.get("content"), list):
                    for item_content in m.get("content", []):
                        if isinstance(item_content, dict) and item_content.get("type") == "text":
                            input_tokens_content += item_content.get("text", "")
            if system_message:
                input_tokens_content += system_message

            input_tokens = len(token_encoder.encode(input_tokens_content))

            end_time = time.time()
            elapsed = round(end_time - start_time, 2)
            stream_elapsed = end_time - stream_start_time

            self.app.logger.info(f"Response completed: {model}, {input_tokens} input tokens, {final_output_tokens if final_output_tokens > 0 else 'N/A'} output tokens, {elapsed}s, {chunk_count} chunks, {round(chunk_count / stream_elapsed, 2) if stream_elapsed > 0 else 0} chunks/sec")
            if final_output_tokens > 0:
                await get_instance().add_use(model, input_tokens, final_output_tokens)
            if task_id:
                self.app.ui.update_task_info(worker_id=task_id, update={"input_tokens": input_tokens, "output_tokens": final_output_tokens if final_output_tokens > 0 else output_tokens_estimate, "tokens_per_second": round((final_output_tokens if final_output_tokens > 0 else output_tokens_estimate) / stream_elapsed, 2) if stream_elapsed > 0 else 0})

        except Exception as e:
            self.app.logger.error(f"Error making Anthropic API request: {str(e)}")
            raise ValueError(f"Error making Anthropic API request: {str(e)}")
