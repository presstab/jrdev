import asyncio
import inspect

import pytest


def pytest_configure(config):
    # Register the asyncio marker so pytest doesn't warn about it.
    config.addinivalue_line("markers", "asyncio: mark test as asyncio-based")


def pytest_pyfunc_call(pyfuncitem):
    """Minimal async test support without external plugins.

    If a test function is defined with ``async def``, run it inside a fresh
    event loop using ``asyncio.run``. This mirrors the basic behavior provided
    by pytest-asyncio for our simple async tests.
    """
    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        asyncio.run(test_func(**pyfuncitem.funcargs))
        return True
    return None

