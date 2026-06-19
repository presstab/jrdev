import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.services.streaming.openai_stream import stream_openai_format


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class FakeUsage:
    async def add_use(self, _model, _input_tokens, _output_tokens):
        return None


class FakeStream:
    def __aiter__(self):
        self._chunks = iter(
            [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))],
                    usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
                )
            ]
        )
        return self

    async def __anext__(self):
        try:
            return next(self._chunks)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeCompletions:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeStream()


class FakeClient:
    def __init__(self):
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


class FakeClients:
    def __init__(self, client):
        self.client = client

    def get_all_clients(self):
        return {"open_router": self.client}

    def get_client(self, provider):
        if provider == "open_router":
            return self.client
        return None


class TestOpenAIStream(unittest.TestCase):
    def test_openrouter_quantizations_sent_as_provider_routing(self):
        client = FakeClient()
        app = SimpleNamespace(
            logger=MagicMock(),
            ui=MagicMock(),
            state=SimpleNamespace(clients=FakeClients(client)),
            get_models=lambda: [
                {
                    "name": "openai/glm-5",
                    "provider": "open_router",
                    "quantizations": ["int4", "int8"],
                }
            ],
        )

        async def consume():
            chunks = []
            async for chunk in stream_openai_format(app, "openai/glm-5", [{"role": "user", "content": "hi"}]):
                chunks.append(chunk)
            return "".join(chunks)

        with patch("jrdev.services.streaming.openai_stream.get_instance", return_value=FakeUsage()):
            response = run_async(consume())

        self.assertEqual(response, "ok")
        self.assertEqual(
            client.completions.kwargs["extra_body"],
            {"provider": {"quantizations": ["int4", "int8"]}},
        )


if __name__ == "__main__":
    unittest.main()
