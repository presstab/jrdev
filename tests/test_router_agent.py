from types import SimpleNamespace

import pytest

from jrdev.agents import router_agent as router_agent_module
from jrdev.agents.router_agent import CommandInterpretationAgent
from jrdev.core.tool_call import ToolCall


class FakeLogger:
    def error(self, *args, **kwargs):  # pragma: no cover - logging helper
        pass


class FakeThread:
    def __init__(self):
        self.messages = []

    def add_message(self, role, content, model=None, metadata=None):
        message = {"role": role, "content": content}
        if model:
            message["model"] = model
        if metadata:
            message["metadata"] = metadata
        self.messages.append(message)

    def add_user_message(self, content, model=None, metadata=None):
        self.add_message("user", content, model=model, metadata=metadata)

    def add_response(self, response, model=None):
        self.add_message("assistant", response, model=model)


class FakeCommandHandler:
    def get_commands(self):
        return {}


class FakeProfileManager:
    def get_model(self, profile_name):
        return f"{profile_name}-model"


class FakeUI:
    def __init__(self):
        self.messages = []

    def print_text(self, message, print_type=None):
        self.messages.append((message, print_type))


class FakeApp:
    def __init__(self):
        self.logger = FakeLogger()
        self.command_handler = FakeCommandHandler()
        self.state = SimpleNamespace(project_files={})
        self.ui = FakeUI()

    def profile_manager(self):
        return FakeProfileManager()


def make_router_agent():
    agent = CommandInterpretationAgent.__new__(CommandInterpretationAgent)
    agent.app = FakeApp()
    agent.logger = agent.app.logger
    agent.thread = FakeThread()
    return agent


def test_record_user_request_is_idempotent_for_turn_id():
    agent = make_router_agent()

    returned_turn_id = agent.record_user_request("show git status", "turn-1")
    repeated_turn_id = agent.record_user_request("show git status", "turn-1")

    assert returned_turn_id == "turn-1"
    assert repeated_turn_id == "turn-1"
    assert agent.thread.messages == [
        {
            "role": "user",
            "content": "**User Request**: show git status",
            "metadata": {
                "type": "router_event",
                "event": "user_request",
                "router_turn_id": "turn-1",
            },
        }
    ]


@pytest.mark.asyncio
async def test_interpret_records_request_once_and_only_adds_observations_on_later_iterations(monkeypatch):
    agent = make_router_agent()
    captured_messages = []

    async def fake_generate_llm_response(app, model, messages, task_id=None):
        captured_messages.append(messages)
        return """```json
{
  "decision": "summary",
  "reasoning": "done",
  "response": "done"
}
```"""

    monkeypatch.setattr(router_agent_module, "generate_llm_response", fake_generate_llm_response)

    await agent.interpret("inspect router state", "worker-1", [], router_turn_id="turn-1")
    await agent.interpret(
        "inspect router state",
        "worker-1",
        [
            ToolCall(
                action_type="tool",
                command="read_files",
                args=["src/jrdev/agents/router_agent.py"],
                reasoning="inspect implementation",
                result="file contents",
                has_next=True,
            )
        ],
        router_turn_id="turn-1",
    )

    user_request_messages = [
        msg
        for msg in agent.thread.messages
        if msg.get("role") == "user"
        and msg.get("metadata", {}).get("event") == "user_request"
        and msg.get("metadata", {}).get("router_turn_id") == "turn-1"
    ]
    assert len(user_request_messages) == 1

    first_prompt_user_messages = [msg["content"] for msg in captured_messages[0] if msg["role"] == "user"]
    assert first_prompt_user_messages == ["inspect router state"]

    later_prompt_user_messages = [msg["content"] for msg in captured_messages[1] if msg["role"] == "user"]
    assert later_prompt_user_messages[0] == "**User Request**: inspect router state"
    assert later_prompt_user_messages[-1].startswith("\n--- Previous Assistant Actions For This User Request ---")
    assert "Command Entered: read_files src/jrdev/agents/router_agent.py" in later_prompt_user_messages[-1]
    assert "Command Results: file contents" in later_prompt_user_messages[-1]
    assert "inspect router state" not in later_prompt_user_messages[-1]
