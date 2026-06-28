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
        self.add_message_calls = []

    def add_message(self, role, content, model=None, metadata=None):
        self.add_message_calls.append(
            {
                "role": role,
                "content": content,
                "model": model,
                "metadata": metadata,
            }
        )
        message = {"role": role, "content": content}
        if model:
            message["model"] = model
        if metadata:
            message["metadata"] = metadata
        self.messages.append(message)

    def add_user_message(self, content, model=None, metadata=None):
        self.add_message("user", content, model=model, metadata=metadata)


class FakeInterpretationAgent:
    def __init__(self, responses):
        self._responses = list(responses)
        self.thread = FakeThread()

    async def interpret(self, *_args, **_kwargs):
        if not self._responses:
            return None
        return self._responses.pop(0)


class TrackingInterpretationAgent(FakeInterpretationAgent):
    def __init__(self, responses):
        super().__init__(responses)
        self.recorded_turns = []
        self.interpret_calls = []

    def record_user_request(self, user_input, router_turn_id=None):
        self.recorded_turns.append((user_input, router_turn_id))
        self.thread.add_user_message(
            f"**User Request**: {user_input}",
            metadata={
                "type": "router_event",
                "event": "user_request",
                "router_turn_id": router_turn_id,
            },
        )
        return router_turn_id

    async def interpret(self, user_input, worker_id, previous_tool_calls=None, router_turn_id=None):
        self.interpret_calls.append(
            {
                "user_input": user_input,
                "worker_id": worker_id,
                "previous_tool_calls": list(previous_tool_calls or []),
                "router_turn_id": router_turn_id,
            }
        )
        return await super().interpret(user_input, worker_id, previous_tool_calls, router_turn_id=router_turn_id)


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


def test_append_thread_message_uses_thread_api():
    app = FakeApp()
    agent = FakeInterpretationAgent([])
    handler = InputHandler(app)

    handler._append_thread_message(agent, "persist this")

    assert agent.thread.add_message_calls == [
        {
            "role": "assistant",
            "content": "persist this",
            "model": None,
            "metadata": None,
        }
    ]
    assert agent.thread.messages == [{"role": "assistant", "content": "persist this"}]


@pytest.mark.asyncio
async def test_route_records_one_user_request_and_reuses_turn_id(monkeypatch):
    def fake_web_search(args):
        return f"result for {args[0]}"

    from jrdev.agents import agent_tools as tools_module

    monkeypatch.setattr(tools_module, "web_search", fake_web_search)

    continuing_call = ToolCall(
        action_type="tool",
        command="web_search",
        args=["router turn state"],
        reasoning="gather context",
        has_next=True,
    )

    app = FakeApp()
    agent = TrackingInterpretationAgent([continuing_call, None])
    app.router_agent = agent
    handler = InputHandler(app)

    result = await handler.route("search router turn state", worker_id="worker-1")

    assert result == "result for router turn state"
    assert len(agent.recorded_turns) == 1
    assert len(agent.interpret_calls) == 2

    router_turn_id = agent.recorded_turns[0][1]
    assert router_turn_id
    assert {call["router_turn_id"] for call in agent.interpret_calls} == {router_turn_id}
    assert agent.interpret_calls[0]["previous_tool_calls"] == []
    assert agent.interpret_calls[1]["previous_tool_calls"] == [continuing_call]

    user_request_messages = [
        msg
        for msg in agent.thread.messages
        if msg.get("role") == "user"
        and msg.get("metadata", {}).get("event") == "user_request"
        and msg.get("metadata", {}).get("router_turn_id") == router_turn_id
    ]
    assert len(user_request_messages) == 1
