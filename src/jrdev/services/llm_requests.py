from asyncio import CancelledError
from typing import AsyncIterator

from jrdev.services import provider_factory
from jrdev.services.streaming.anthropic_streamer import AnthropicStreamer
from jrdev.services.streaming.openai_streamer import OpenAIStreamer


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