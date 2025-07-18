import asyncio
from functools import wraps
from typing import AsyncIterator, Callable, Any


class RetryableStreamError(Exception):
    """Raised when a stream fails and should be retried."""
    pass


def retry_stream(max_attempts: int = 2, backoff: float = 0.5):
    """
    Decorator that retries an async streaming function up to `max_attempts` times.
    Only retries on RetryableStreamError or other non-CancelledError exceptions.
    """
    def decorator(func: Callable[..., AsyncIterator[str]]):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> AsyncIterator[str]:
            attempt = 0
            while True:
                try:
                    async for chunk in func(*args, **kwargs):
                        yield chunk
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    await asyncio.sleep(backoff * (2 ** (attempt - 1)))
        return wrapper
    return decorator


async def filter_think_tags(stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """
    Middleware that filters out <think>...</think> blocks from an async string stream.
    """
    first_chunk = True
    in_think = False
    thinking_finish = False

    async for chunk in stream:
        if first_chunk:
            first_chunk = False
            if chunk == "<think>":
                in_think = True
                continue
            else:
                yield chunk
        elif in_think:
            if chunk == "</think>":
                in_think = False
                thinking_finish = True
            continue
        else:
            if thinking_finish:
                while chunk.startswith("\n"):
                    chunk = chunk.removeprefix("\n")
                thinking_finish = False
            yield chunk