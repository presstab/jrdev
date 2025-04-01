import re
import time

from jrdev.model_utils import is_think_model
from jrdev.ui.ui import terminal_print, PrintType
from jrdev.usage import get_instance


def filter_think_tags(text):
    """Remove content within <think></think> tags."""
    # Use regex to remove all <think>...</think> sections
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)


def is_inside_think_tag(text):
    """Determine if the current position is inside a <think> tag."""
    # Count the number of opening and closing tags
    think_open = text.count("<think>")
    think_close = text.count("</think>")

    # If there are more opening tags than closing tags, we're inside a tag
    return think_open > think_close


async def stream_openai_format(terminal, model, messages, print_stream=True, json_output=False):
    # Start timing the response
    start_time = time.time()

    log_msg = f"Sending request to {model} with {len(messages)} messages"
    terminal.logger.info(log_msg)
    
    # Get the appropriate client
    model_provider = None

    # Find the model in AVAILABLE_MODELS
    available_models = terminal.get_models()
    for entry in available_models:
        if entry["name"] == model:
            model_provider = entry["provider"]
            break

    # Select the appropriate client based on provider
    if model_provider == "venice":
        client = terminal.venice_client
    elif model_provider == "openai":
        client = terminal.openai_client
        if not client:
            raise ValueError(f"OpenAI API key not configured but model {model} requires it")
    elif model_provider == "deepseek":
        client = terminal.deepseek_client
        if not client:
            raise ValueError(f"DeepSeek API key not configured but model {model} requires it")
    else:
        raise ValueError(f"Unknown provider for model {model}")

    # Create a streaming completion
    kwargs = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.0
    }

    if model_provider == "openai":
        if "o3-mini" in model:
            kwargs["reasoning_effort"] = "high"
            #o3-mini incompatible with temp
            del kwargs["temperature"]
    elif model == "qwen-2.5-qwq-32b":
        kwargs["top_p"] = 0.95
        kwargs["extra_body"] = {"venice_parameters":{"include_venice_system_prompt": False}, "frequency_penalty": 0.3}
    elif model == "deepseek-r1-671b":
        kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}}
    elif model == "deepseek-reasoner" or model == "deepseek-chat":
        kwargs["max_tokens"] = 8000
        if model == "deepseek-chat" and json_output:
            kwargs["response_format"] = {"type": "json_object"}
    else:
        kwargs["extra_body"] = {"venice_parameters": {"include_venice_system_prompt": False}}

    stream = await client.chat.completions.create(**kwargs)

    uses_think = is_think_model(model, terminal.get_models())
    response_text = ""
    first_chunk = True
    chunk_count = 0
    log_interval = 100  # Log every 100 chunks
    stream_start_time = None  # Track when we start receiving chunks

    async for chunk in stream:
        if first_chunk:
            # Update status message when first chunk arrives
            stream_start_time = time.time()  # Start timing from first chunk
            if print_stream:
                terminal_print(f"Receiving response from {model}...", PrintType.PROCESSING)
            terminal.logger.info(f"Started receiving response from {model}")
            first_chunk = False
        
        chunk_count += 1
        if chunk_count % log_interval == 0:
            # Calculate chunks per second
            current_time = time.time()
            elapsed_time = current_time - stream_start_time
            chunks_per_second = round(chunk_count / elapsed_time, 2) if elapsed_time > 0 else 0
            
            terminal.logger.info(f"Received {chunk_count} chunks from {model} ({chunks_per_second} chunks/sec)")

        # Handle OpenAI-compatible chunks (Venice and OpenAI)
        if chunk.choices and chunk.choices[0].delta.content:
            chunk_text = chunk.choices[0].delta.content
            response_text += chunk_text

            # For DeepSeek models, only print content that's not in <think> tags
            if uses_think:
                # Check if this chunk contains any complete </think> tags
                # If so, we need to recalculate what to display from the full text
                if "</think>" in chunk_text:
                    filtered_text = filter_think_tags(response_text)

                    # Print only new content since last filtered output
                    if len(filtered_text) > 0:
                        if print_stream:
                            terminal_print(
                                filtered_text[-len(chunk_text):],
                                PrintType.LLM,
                                end="",
                                flush=True
                            )
                else:
                    # For chunks without </think>, we check if we're currently inside a tag
                    in_think_tag = is_inside_think_tag(response_text)
                    if not in_think_tag and chunk_text:
                        if print_stream:
                            terminal_print(chunk_text, PrintType.LLM, end="", flush=True)
            else:
                # For non-think models, print all chunks
                if print_stream:
                    terminal_print(chunk_text, PrintType.LLM, end="", flush=True)

    # Handle token usage statistics for final chunk
    if "completion_tokens" in str(chunk):
        # Handle OpenAI-compatible usage stats (Venice and OpenAI)
        input_tokens = chunk.usage.prompt_tokens
        output_tokens = chunk.usage.completion_tokens

        # Calculate elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_seconds = round(elapsed_time, 2)
        
        # Calculate chunks per second over the entire response
        stream_elapsed = end_time - (stream_start_time or start_time)
        chunks_per_second = round(chunk_count / stream_elapsed, 2) if stream_elapsed > 0 else 0

        if print_stream:
            terminal_print(
                f"\nInput Tokens: {input_tokens} | Output Tokens: {output_tokens} | "
                f"Response Time: {elapsed_seconds}s | Avg: {chunks_per_second} chunks/sec",
                PrintType.WARNING
            )

        # Log completion stats
        terminal.logger.info(
            f"Response completed: {model}, {input_tokens} input tokens, {output_tokens} output tokens, "
            f"{elapsed_seconds}s, {chunk_count} chunks, {chunks_per_second} chunks/sec"
        )
        
        # Track token usage
        usage_tracker = get_instance()
        await usage_tracker.add_use(model, input_tokens, output_tokens)

    if uses_think:
        return filter_think_tags(response_text)
    else:
        return response_text

async def stream_messages_format(terminal, model, messages, print_stream=True):
    # Start timing the response
    start_time = time.time()
    
    # Log the request with context file names
    context_files = []
    for message in messages:
        if "Supporting Context" in message.get("content", ""):
            # Extract file names from context message
            content = message["content"]
            if "Context File" in content:
                # Extract file names from the context sections
                for line in content.split("\n"):
                    if "Context File" in line and ":" in line:
                        try:
                            file_name = line.split(":", 1)[1].strip()
                            context_files.append(file_name)
                        except IndexError:
                            pass

    log_msg = f"Sending request to {model} with {len(messages)} messages"
    if context_files:
        log_msg += f", context files: {', '.join(context_files)}"
    terminal.logger.info(log_msg)
    
    # Get Anthropic client
    client = terminal.anthropic_client
    if not client:
        raise ValueError(f"Anthropic API key not configured but model {model} requires it")
    
    # Convert OpenAI message format to Anthropic format
    anthropic_messages = []
    system_message = None
    
    # Extract system message if present
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
            
    # Process other messages
    for msg in messages:
        role = msg["role"]
        # Map OpenAI roles to Anthropic roles (skip system as it's handled separately)
        if role == "user":
            anthropic_messages.append({"role": "user", "content": msg["content"]})
        elif role == "assistant":
            anthropic_messages.append({"role": "assistant", "content": msg["content"]})
        # Don't include system messages in the anthropic_messages list
    
    response_text = ""
    chunk_count = 0
    log_interval = 100  # Log every 100 chunks
    
    try:
        # Create Claude streaming completion
        # Ensure system_message is passed correctly
        kwargs = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "temperature": 0.0
        }
        
        # Only add system if it's not None
        if system_message is not None:
            kwargs["system"] = system_message
            
        stream_manager = client.messages.stream(**kwargs)
        
        # Start the streaming session with the context manager
        if print_stream:
            terminal_print(f"Receiving response from {model}...", PrintType.PROCESSING)
        terminal.logger.info(f"Started receiving response from {model}")
        stream_start_time = time.time()
        
        async with stream_manager as stream:
            # Process each event from the stream
            async for chunk in stream:
                if chunk.type == 'content_block_delta':
                    if hasattr(chunk.delta, 'text'):
                        chunk_text = chunk.delta.text
                        response_text += chunk_text
                        if print_stream:
                            terminal_print(chunk_text, PrintType.LLM, end="", flush=True)
                
                # Count each chunk for logging
                chunk_count += 1
                if chunk_count % log_interval == 0:
                    # Calculate chunks per second
                    current_time = time.time()
                    elapsed_time = current_time - stream_start_time
                    chunks_per_second = round(chunk_count / elapsed_time, 2) if elapsed_time > 0 else 0
                    terminal.logger.info(f"Received {chunk_count} chunks from {model} ({chunks_per_second} chunks/sec)")
                
            # Get usage information after stream is complete
            if hasattr(stream, 'usage'):
                input_tokens = getattr(stream.usage, 'input_tokens', 0)
                output_tokens = getattr(stream.usage, 'output_tokens', 0)
                
                # Calculate elapsed time
                end_time = time.time()
                elapsed_time = end_time - start_time
                elapsed_seconds = round(elapsed_time, 2)
                
                # Calculate chunks per second over the entire response
                stream_elapsed = end_time - stream_start_time
                chunks_per_second = round(chunk_count / stream_elapsed, 2) if stream_elapsed > 0 else 0
                
                if print_stream:
                    terminal_print(
                        f"\nInput Tokens: {input_tokens} | Output Tokens: {output_tokens} | "
                        f"Response Time: {elapsed_seconds}s | Avg: {chunks_per_second} chunks/sec",
                        PrintType.WARNING
                    )
                
                # Log completion stats
                terminal.logger.info(
                    f"Response completed: {model}, {input_tokens} input tokens, {output_tokens} output tokens, "
                    f"{elapsed_seconds}s, {chunk_count} chunks, {chunks_per_second} chunks/sec"
                )
                
                # Track token usage
                usage_tracker = get_instance()
                await usage_tracker.add_use(model, input_tokens, output_tokens)
            
            # Return the complete response text for Anthropic
            return response_text
                
    except Exception as e:
        terminal.logger.error(f"Error making Anthropic API request: {str(e)}")
        raise ValueError(f"Error making Anthropic API request: {str(e)}")

async def stream_request(terminal, model, messages, print_stream=True, json_output=False):
    # Determine which client to use based on the model provider
    model_provider = None

    # Find the model in AVAILABLE_MODELS
    available_models = terminal.get_models()
    for entry in available_models:
        if entry["name"] == model:
            model_provider = entry["provider"]
            break
            
    # Call the appropriate streaming function based on provider
    if model_provider == "anthropic":
        return await stream_messages_format(terminal, model, messages, print_stream)
    else:
        return await stream_openai_format(terminal, model, messages, print_stream, json_output)