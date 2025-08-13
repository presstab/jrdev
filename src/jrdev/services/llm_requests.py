from typing import AsyncIterator
from asyncio import CancelledError

from jrdev.services.streaming.anthropic_stream import stream_anthropic_format
from jrdev.services.streaming.google_stream import stream_gemini_format
from jrdev.services.streaming.openai_stream import stream_openai_format


def stream_request(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None) -> AsyncIterator[str]:
    """Route a streaming LLM request to the appropriate provider based on the model."""
    model_provider = None
    for entry in app.get_models():
        if entry["name"] == model:
            model_provider = entry["provider"]
            break
    if model_provider == "anthropic":
        return stream_anthropic_format(app, model, messages, task_id, print_stream)
    elif model_provider == "gemini":
        return stream_gemini_format(app, model, messages, task_id, print_stream, json_output, max_output_tokens)
    else:
        return stream_openai_format(app, model, messages, task_id, print_stream, json_output, max_output_tokens)

async def generate_llm_response(app, model, messages, task_id=None, print_stream=True, json_output=False, max_output_tokens=None, attempts=0):
    """Consume a streamed LLM response and return the accumulated text.
    Filters out <think>...</think> segments and trims leading newlines that follow.
    """
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