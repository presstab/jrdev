from asyncio import CancelledError
from typing import AsyncIterator

from jrdev.services import provider_factory
from jrdev.services.streaming.anthropic_streamer import AnthropicStreamer
from jrdev.services.streaming.openai_streamer import OpenAIStreamer
from jrdev.services.request_wrapper import retry_stream, filter_think_tags


def stream_request(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None) -> AsyncIterator[str]:
    """
    Dispatches the streaming request to the appropriate provider streamer.
    """
    model_provider = provider_factory.get_provider_for_model(model)

    if model_provider == "anthropic":
        streamer = AnthropicStreamer(app.logger, app.ui, app.usageTracker)
        # Anthropic streamer doesn't use json_output or max_output_tokens in its signature
        return streamer.stream(model, messages, task_id)
    else:
        streamer = OpenAIStreamer(app.logger, app.ui, app.usageTracker)
        return streamer.stream(
            model,
            messages,
            task_id,
            json_output=json_output,
            max_output_tokens=max_output_tokens
        )


async def generate_llm_response(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None) -> str:
    """
    Streams the LLM response, applies retry logic and <think> tag filtering,
    and returns the complete response as a string.
    """
    
    @retry_stream(max_attempts=2)
    async def _stream_with_retry():
        llm_response_stream = stream_request(app, model, messages, task_id, print_stream, json_output, max_output_tokens)
        filtered_stream = filter_think_tags(llm_response_stream)

        async for chunk in filtered_stream:
            yield chunk
    
    response_accumulator = ""
    async for chunk in _stream_with_retry():
        response_accumulator += chunk

    return response_accumulator