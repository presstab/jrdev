import asyncio
from types import SimpleNamespace

import pytest

from jrdev.core.input_handler import InputHandler
from jrdev.core.tool_call import ToolCall
from jrdev.ui.ui import PrintType


class FakeLogger:
    def info(self, *args, **kwargs):  # pragma: no cover - logging helper
        pass

    def warning(self, *args, **kwargs):  # pragma: no cover - logging helper
        pass

    def error(self, *args, **kwargs):  # pragma: no cover - logging helper
        pass


class FakeUI:
    def __init__(self):
        self.messages = []
        self._capturing = False
        self._capture_buffer = []

    def print_text(self, message, print_type=None):
        self.messages.append((message, print_type))
        if self._capturing:
            self._capture_buffer.append(message)

    def start_capture(self):
        self._capturing = True
        self._capture_buffer = []

    def end_capture(self):
        self._capturing = False

    def get_capture(self):
        return "\n".join(self._capture_buffer)

    async def prompt_for_command_confirmation(self, command_str):
        self.messages.append((f"confirm:{command_str}", PrintType.INFO))
        return True


class FakeApp:
    def __init__(self):
        self.logger = FakeLogger()
        self.ui = FakeUI()
        self.user_settings = SimpleNamespace(max_router_iterations=3)
        self.state = SimpleNamespace(running=True)
        self.commands_executed = []
        self.router_agent = None

    async def handle_command(self, command):
        self.commands_executed.append(command.text)
        self.ui.print_text(f"handled {command.text}", PrintType.INFO)
        await asyncio.sleep(0)


class FakeThread:
    def __init__(self):
        self.messages = []


class FakeInterpretationAgent:
    def __init__(self, responses):
        self._responses = list(responses)
        self.thread = FakeThread()

    async def interpret(self, *_args, **_kwargs):
        if not self._responses:
            return None
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_route_executes_command_and_captures_output():
    tool_call = ToolCall(
        action_type="command",
        command="/echo",
        args=["hello", "world"],
        reasoning="echo the greeting",
        has_next=False,
    )
    app = FakeApp()
    agent = FakeInterpretationAgent([tool_call])
    app.router_agent = agent
    handler = InputHandler(app)

    result = await handler.route("echo hello")

    assert app.commands_executed == ["/echo hello world"]
    assert tool_call.result == "handled /echo hello world"
    assert result == tool_call.result
    assert agent.thread.messages[-1]["content"] == "handled /echo hello world"


@pytest.mark.asyncio
async def test_route_stores_tool_results_in_thread(monkeypatch):
    calls = {"count": 0}

    def fake_web_search(args):
        calls["count"] += 1
        return f"result {calls['count']} for {args[0]}"

    from jrdev.agents import agent_tools as tools_module

    monkeypatch.setattr(tools_module, "web_search", fake_web_search)

    tool_calls = [
        ToolCall(
            action_type="tool",
            command="web_search",
            args=["python caching"],
            reasoning="search the web",
            has_next=False,
        ),
        ToolCall(
            action_type="tool",
            command="web_search",
            args=["python caching"],
            reasoning="search the web",
            has_next=False,
        ),
    ]

    app = FakeApp()
    agent = FakeInterpretationAgent(tool_calls)
    app.router_agent = agent
    handler = InputHandler(app)

    result = await handler.route("search python caching")

    assert calls["count"] == 1
    assert result == "result 1 for python caching"
    assert agent.thread.messages[-1]["content"] == "result 1 for python caching"
