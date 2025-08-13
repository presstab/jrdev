import time
from typing import AsyncIterator

import tiktoken
from google import genai as genai
from google.genai import types as genai_types

from jrdev.core.usage import get_instance


async def stream_gemini_format(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None) -> AsyncIterator[str]:
    if not genai or not genai_types:
        app.logger.error("google-genai library not installed, but a Gemini model was requested.")
        raise ImportError("google-genai library is not installed. Please install it with 'pip install google-genai'")

    start_time = time.time()
    log_msg = f"Sending request to Gemini model {model} with {len(messages)} messages"
    app.logger.info(log_msg)

    client = app.state.clients.get_client("gemini")
    if not client:
        raise ValueError("Gemini client not initialized. Check API key.")

    # Convert messages to Gemini format
    gemini_contents = []
    system_instruction = None

    non_system_messages = []
    for msg in messages:
        if msg["role"] == "system":
                system_instruction = msg['content']
        else:
            non_system_messages.append(msg)

    for msg in non_system_messages:
        role = "user" if msg["role"] == "user" else "model"
        content = msg.get("content")
        parts = []
        if isinstance(content, str):
            parts.append({'text': content})
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    parts.append({'text': item.get("text", "")})

        if parts:
            gemini_contents.append({'role': role, 'parts': parts})

    # Prepare generation config
    generation_config_kwargs = {"temperature": 0.0}
    if max_output_tokens:
        generation_config_kwargs['max_output_tokens'] = max_output_tokens
    if json_output:
        generation_config_kwargs['response_mime_type'] = 'application/json'
    if system_instruction:
        generation_config_kwargs['system_instruction'] = system_instruction.split("\n")

    generation_config = genai_types.GenerateContentConfig(**generation_config_kwargs)

    # Token estimation
    token_encoder = tiktoken.get_encoding("cl100k_base")
    if task_id:
        try:
            count_tokens_response = await client.aio.models.count_tokens(
                model=model,
                contents=gemini_contents
            )
            input_tokens = count_tokens_response.total_tokens
            app.ui.update_task_info(task_id, update={"input_token_estimate": input_tokens, "model": model})
        except Exception as e:
            app.logger.error(f"Error estimating Gemini input tokens via API: {e}. Falling back to tiktoken.")
            input_chunk_content = ""
            for msg in messages:
                if "content" in msg and isinstance(msg["content"], str):
                    input_chunk_content += msg["content"]
                elif isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if isinstance(item, dict) and item.get("type") == "text":
                            input_chunk_content += item.get("text", "")
            input_token_estimate = token_encoder.encode(input_chunk_content)
            app.ui.update_task_info(task_id, update={"input_token_estimate": len(input_token_estimate), "model": model})

    # Create stream
    stream_kwargs = {
        "model": model,
        "contents": gemini_contents,
        "config": generation_config,
    }

    stream = await client.aio.models.generate_content_stream(**stream_kwargs)

    first_chunk = True
    chunk_count = 0
    log_interval = 100
    stream_start_time = None
    output_tokens_estimate = 0
    final_usage_metadata = None

    async for chunk in stream:
        if first_chunk:
            stream_start_time = time.time()
            app.logger.info(f"Started receiving response from Gemini model {model}")
            first_chunk = False

        chunk_count += 1
        if chunk_count % log_interval == 0 and stream_start_time:
            elapsed = time.time() - stream_start_time
            app.logger.info(f"Received {chunk_count} chunks from {model} ({round(chunk_count/elapsed,2) if elapsed > 0 else 0} chunks/sec)")

        try:
            chunk_text = chunk.text
            if chunk_text:
                if task_id:
                    try:
                        tokens = token_encoder.encode(chunk_text)
                        output_tokens_estimate += len(tokens)
                        if chunk_count % 10 == 0 and stream_start_time:
                            elapsed = time.time() - stream_start_time
                            app.ui.update_task_info(worker_id=task_id, update={"output_token_estimate": output_tokens_estimate, "tokens_per_second": (output_tokens_estimate)/elapsed if elapsed>0 else 0})
                    except Exception as e:
                        app.logger.error(f"Error estimating output tokens for chunk: {e}")
                yield chunk_text
        except ValueError as e:
            app.logger.warning(f"ValueError accessing chunk.text from Gemini, possibly blocked content: {e}")

        if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
            final_usage_metadata = chunk.usage_metadata

    end_time = time.time()
    elapsed_seconds = round(end_time - start_time, 2)
    stream_elapsed = end_time - (stream_start_time or start_time)

    if final_usage_metadata:
        input_tokens = final_usage_metadata.prompt_token_count
        output_tokens = final_usage_metadata.candidates_token_count
        if task_id:
            app.ui.update_task_info(worker_id=task_id, update={"input_tokens": input_tokens, "output_tokens": output_tokens, "tokens_per_second": round(output_tokens/stream_elapsed,2) if stream_elapsed > 0 else 0})
        app.logger.info(f"Response completed: {model}, {input_tokens} input tokens, {output_tokens} output tokens, {elapsed_seconds}s, {chunk_count} chunks, {round(chunk_count/stream_elapsed,2) if stream_elapsed > 0 else 0} chunks/sec")
        await get_instance().add_use(model, input_tokens, output_tokens)
    elif stream_start_time:
        app.logger.info(f"Response completed (no usage data in final chunk): {model}, {elapsed_seconds}s, {chunk_count} chunks, {round(chunk_count/stream_elapsed,2) if stream_elapsed > 0 else 0} chunks/sec")
