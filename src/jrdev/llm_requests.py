import re
import time
from jrdev.colors import Colors
from jrdev.ui.ui import terminal_print, PrintType
from jrdev.model_utils import is_think_model
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


async def stream_request(terminal, model, messages, print_stream=True):
    # Start timing the response
    start_time = time.time()
    
    # Determine which client to use based on the model provider
    client = None
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
    else:
        raise ValueError(f"Unknown provider for model {model}")
    
    # Create a streaming completion
    if model_provider == "openai":
        if model == "o3-mini":
            stream = await client.chat.completions.create(model=model, messages=messages, stream=True, reasoning_effort="high")
        else:
            stream = await client.chat.completions.create(model=model, messages=messages, stream=True, temperature=0.0)
    elif model == "qwen-2.5-qwq-32b":
        stream = await client.chat.completions.create(
            model=model, messages=messages, stream=True, temperature=0.0, top_p=0.95,
            extra_body={"venice_parameters":{"include_venice_system_prompt": False}, "frequency_penalty": 0.3}
        )
    elif model == "deepseek-r1-671b":
        stream = await client.chat.completions.create(
            model=model, messages=messages, stream=True, temperature=0.0,
            extra_body={"venice_parameters":{"include_venice_system_prompt":False}, "frequency_penalty": 0.3}
        )
    else:
        stream = await client.chat.completions.create(
            model=model, messages=messages, stream=True, temperature=0.0,
            extra_body={"venice_parameters": {"include_venice_system_prompt": False}}
        )

    uses_think = is_think_model(model, terminal.get_models())
    response_text = ""
    first_chunk = True

    async for chunk in stream:
        if first_chunk:
            # Update status message when first chunk arrives
            if print_stream:
                terminal_print(f"Receiving response from {model}...", PrintType.PROCESSING)
            first_chunk = False

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

        if "completion_tokens" in str(chunk):
            # print(chunk)
            # print(chunk.usage.completion_tokens)
            input_tokens = chunk.usage.prompt_tokens
            output_tokens = chunk.usage.completion_tokens
            
            # Calculate elapsed time
            end_time = time.time()
            elapsed_time = end_time - start_time
            elapsed_seconds = round(elapsed_time, 2)
            
            if print_stream:
                terminal_print(f"\nInput Tokens: {input_tokens} | Output Tokens: {output_tokens} | Response Time: {elapsed_seconds}s", PrintType.WARNING)
            
            # Track token usage
            usage_tracker = get_instance()
            await usage_tracker.add_use(model, input_tokens, output_tokens)

    if uses_think:
        return filter_think_tags(response_text)
    return response_text
