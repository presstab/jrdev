import time
import tiktoken
from typing import AsyncIterator
from asyncio import CancelledError
from jrdev.core.usage import get_instance


async def stream_openai_format(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None) -> AsyncIterator[str]:
    # Start timing the response
    start_time = time.time()

    log_msg = f"Sending request to {model} with {len(messages)} messages"
    app.logger.info(log_msg)
    
    # Get the appropriate client
    model_provider = None

    # Find the model in AVAILABLE_MODELS
    available_models = app.get_models()
    for entry in available_models:
        if entry["name"] == model:
            model_provider = entry["provider"]
            break

    # token estimator
    token_encoder = tiktoken.get_encoding("cl100k_base")

    # Select the appropriate client based on provider
    if model_provider not in app.state.clients.get_all_clients():
        raise ValueError(f"No client for {model_provider}")
    client = app.state.clients.get_client(model_provider)

    # Create a streaming completion
    kwargs = {
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
        kwargs["max_completion_tokens"] = max_output_tokens

    if model_provider == "openai":
        if "o3" in model or "o4-mini" in model:
            kwargs["reasoning_effort"] = "high"
            del kwargs["temperature"]
        kwargs["stream_options"] = {"include_usage": True}
    elif model == "qwen-2.5-qwq-32b":
        kwargs["top_p"] = 0.95
        kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}, "frequency_penalty": 0.3}
    elif model == "deepseek-r1-671b":
        kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}}
    elif model == "deepseek-reasoner" or model == "deepseek-chat":
        kwargs["max_tokens"] = 8000
        if model == "deepseek-chat" and json_output:
            kwargs["response_format"] = {"type": "json_object"}
    elif model_provider == "venice":
        kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}}
    elif model_provider == "open_router" and "deepseek" in model:
        kwargs["extra_body"] = {"provider": {"order": ["Lambda"], "allow_fallbacks": False, "require_parameters": True}}

    stream = await client.chat.completions.create(**kwargs)

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
            app.ui.update_task_info(task_id, update={"input_token_estimate": len(input_token_estimate), "model": model})
        except Exception as e:
            app.logger.error(f"Error estimating input tokens: {e}")

    output_tokens_estimate = 0
    final_chunk_data = None
    async for chunk in stream:
        if first_chunk:
            stream_start_time = time.time()
            app.logger.info(f"Started receiving response from {model}")
            first_chunk = False
        chunk_count += 1
        if chunk_count % log_interval == 0 and stream_start_time:
            elapsed = time.time() - stream_start_time
            app.logger.info(f"Received {chunk_count} chunks from {model} ({round(chunk_count/elapsed,2) if elapsed > 0 else 0} chunks/sec)")

        if chunk.choices and chunk.choices[0].delta.content:
            chunk_text = chunk.choices[0].delta.content
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
        final_chunk_data = chunk # Store the last chunk to access usage data if available

    if final_chunk_data and hasattr(final_chunk_data, 'usage') and final_chunk_data.usage:
        input_tokens = final_chunk_data.usage.prompt_tokens
        output_tokens = final_chunk_data.usage.completion_tokens
        end_time = time.time()
        elapsed_seconds = round(end_time - start_time, 2)
        stream_elapsed = end_time - (stream_start_time or start_time)
        if task_id:
            app.ui.update_task_info(worker_id=task_id, update={"input_tokens": input_tokens, "output_tokens": output_tokens, "tokens_per_second": round(output_tokens/stream_elapsed,2) if stream_elapsed > 0 else 0})
        app.logger.info(f"Response completed: {model}, {input_tokens} input tokens, {output_tokens} output tokens, {elapsed_seconds}s, {chunk_count} chunks, {round(chunk_count/stream_elapsed,2) if stream_elapsed > 0 else 0} chunks/sec")
        await get_instance().add_use(model, input_tokens, output_tokens)
    elif stream_start_time: # Fallback if usage not in final chunk but stream happened
        end_time = time.time()
        elapsed_seconds = round(end_time - start_time, 2)
        stream_elapsed = end_time - stream_start_time
        app.logger.info(f"Response completed (no usage data in final chunk): {model}, {elapsed_seconds}s, {chunk_count} chunks, {round(chunk_count/stream_elapsed,2) if stream_elapsed > 0 else 0} chunks/sec")


async def stream_messages_format(app, model, messages, task_id=None, print_stream=True) -> AsyncIterator[str]:
    start_time = time.time()
    context_files = []
    for m in messages:
        if isinstance(m.get("content"), str) and "Supporting Context" in m.get("content", ""):
            for line in m["content"].split("\n"):
                if "Context File" in line and ":" in line:
                    try:
                        context_files.append(line.split(":",1)[1].strip())
                    except:
                        pass
    log_msg = f"Sending request to {model} with {len(messages)} messages"
    if context_files:
        log_msg += f", context files: {', '.join(context_files)}"
    app.logger.info(log_msg)
    client = app.state.clients.anthropic
    if not client:
        raise ValueError(f"Anthropic API key not configured but model {model} requires it")
    anthropic_messages = []
    system_message = None
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
    for msg in messages:
        if msg["role"] in ("user","assistant"):
            anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
    
    chunk_count = 0
    log_interval = 100
    token_encoder = tiktoken.get_encoding("cl100k_base")
    if task_id:
        try:
            inp_content = ""
            for m in messages:
                if isinstance(m.get("content"), str):
                    inp_content += m.get("content","")
                elif isinstance(m.get("content"), list):
                     for item in m.get("content",[]):
                        if isinstance(item, dict) and item.get("type") == "text":
                            inp_content += item.get("text", "")
            app.ui.update_task_info(task_id, update={"input_token_estimate": len(token_encoder.encode(inp_content)), "model": model})
        except Exception as e:
            app.logger.error(f"Error estimating input tokens for Anthropic: {e}")

    try:
        kwargs = {"model": model, "messages": anthropic_messages, "max_tokens": 8192, "temperature": 0.0}
        if system_message is not None:
            kwargs["system"] = system_message
        stream_manager = client.messages.stream(**kwargs)
        
        app.logger.info(f"Started receiving response from {model}")
        stream_start_time = time.time()
        output_tokens_estimate = 0
        final_output_tokens = 0
        
        async with stream_manager as stream:
            async for chunk in stream:
                if chunk.type == 'content_block_delta' and hasattr(chunk.delta,'text'):
                    ct = chunk.delta.text
                    if task_id:
                        try:
                            tokens = token_encoder.encode(ct)
                            output_tokens_estimate += len(tokens)
                            if chunk_count % 10 == 0 and output_tokens_estimate>0:
                                elapsed = time.time() - stream_start_time
                                app.ui.update_task_info(worker_id=task_id, update={"output_token_estimate": output_tokens_estimate, "tokens_per_second": (output_tokens_estimate)/elapsed if elapsed>0 else 0})
                        except Exception as e:
                            app.logger.error(f"Error estimating output tokens for Anthropic chunk: {e}")
                    yield ct
                elif chunk.type == 'message_delta' and hasattr(chunk,'usage') and hasattr(chunk.usage,'output_tokens'):
                    final_output_tokens += chunk.usage.output_tokens # Accumulate final output tokens from delta
                
                chunk_count += 1
                if chunk_count % log_interval == 0:
                    elapsed = time.time() - stream_start_time
                    app.logger.info(f"Received {chunk_count} chunks from {model} ({round(chunk_count/elapsed,2) if elapsed > 0 else 0} chunks/sec)")
            
            # After stream finishes, get final usage if available in the stream object itself
            # (Anthropic's stream object might provide total usage at the end)
            # For now, we rely on message_delta for output_tokens.
            # Input tokens need to be calculated manually for Anthropic if not provided directly.
            
            input_tokens_content = ""
            for m in messages:
                if isinstance(m.get("content"), str):
                    input_tokens_content += m.get("content","")
                elif isinstance(m.get("content"), list):
                    for item_content in m.get("content",[]):
                        if isinstance(item_content, dict) and item_content.get("type") == "text":
                            input_tokens_content += item_content.get("text", "")
            if system_message:
                 input_tokens_content += system_message

            input_tokens = len(token_encoder.encode(input_tokens_content))
            
            # If final_output_tokens wasn't updated by message_delta, estimate from accumulated text (less accurate)
            # This part is tricky as we don't accumulate response_text anymore.
            # For now, we rely on final_output_tokens from message_delta.
            # If that's zero, it means the SDK didn't provide it incrementally.
            # The SDK docs should be checked for the best way to get final token counts.

            end_time = time.time()
            elapsed = round(end_time - start_time,2)
            stream_elapsed = end_time - stream_start_time
            
            app.logger.info(f"Response completed: {model}, {input_tokens} input tokens, {final_output_tokens if final_output_tokens > 0 else 'N/A'} output tokens, {elapsed}s, {chunk_count} chunks, {round(chunk_count/stream_elapsed,2) if stream_elapsed > 0 else 0} chunks/sec")
            if final_output_tokens > 0:
                await get_instance().add_use(model, input_tokens, final_output_tokens)
            if task_id:
                app.ui.update_task_info(worker_id=task_id, update={"input_tokens": input_tokens, "output_tokens": final_output_tokens if final_output_tokens > 0 else output_tokens_estimate, "tokens_per_second": round((final_output_tokens if final_output_tokens > 0 else output_tokens_estimate)/stream_elapsed,2) if stream_elapsed > 0 else 0})

    except Exception as e:
        app.logger.error(f"Error making Anthropic API request: {str(e)}")
        raise ValueError(f"Error making Anthropic API request: {str(e)}")

def stream_request(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None) -> AsyncIterator[str]:
    model_provider = None
    for entry in app.get_models():
        if entry["name"] == model:
            model_provider = entry["provider"]
            break
    if model_provider == "anthropic":
        return stream_messages_format(app, model, messages, task_id, print_stream)
    else:
        return stream_openai_format(app, model, messages, task_id, print_stream, json_output, max_output_tokens)

async def generate_llm_response(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None, attempts=0):
    # Stream response from LLM and return the full response string
    try:
        llm_response_stream = stream_request(app, model, messages, task_id, print_stream, json_output, max_output_tokens)

        response_accumulator = ""
        first_chunk = True
        in_think = False
        thinking_finish = False
        async for chunk in llm_response_stream:
            # filter out thinking
            if first_chunk:
                first_chunk = False
                if chunk == "<think>":
                    in_think = True
                else:
                    response_accumulator += chunk
            elif in_think:
                if chunk == "</think>":
                    in_think = False
                    thinking_finish = True
            else:
                if thinking_finish:
                    # often the first chunks after thinking will be new lines
                    while chunk.startswith("\n"):
                        chunk = chunk.removeprefix("\n")
                    thinking_finish = False

                response_accumulator += chunk

        return response_accumulator
    except CancelledError:
        # worker.cancel() should kill everything
        raise
    except Exception as e:
        app.logger.error(f"generate_llm_response: {e}")
        if attempts < 1:
            # try again
            app.logger.info("Attempting LLM stream again")
            attempts += 1
            return await generate_llm_response(app, model, messages, task_id, print_stream, json_output, max_output_tokens, attempts)