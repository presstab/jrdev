import json
from uuid import uuid4
from typing import Any, Dict, List, Optional

from jrdev.agents import agent_tools
from jrdev.core.tool_call import ToolCall
from jrdev.messages import MessageThread
from jrdev.messages.message_builder import MessageBuilder
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class CommandInterpretationAgent:
    def __init__(self, app: Any):
        self.app = app
        self.logger = app.logger
        # Use the dedicated system thread for conversation history
        self.thread: MessageThread = self.app.state.get_thread(self.app.state.router_thread_id)

    @staticmethod
    def parse_router_json(response_text: str) -> Dict[str, Any]:
        """Parse a router JSON response even when it contains markdown fences in strings."""
        stripped_response = response_text.strip()
        try:
            parsed = json.loads(stripped_response)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        json_start = stripped_response.find("{")
        if json_start == -1:
            raise json.JSONDecodeError("No JSON object found", stripped_response, 0)

        parsed, _ = json.JSONDecoder().raw_decode(stripped_response[json_start:])
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("Router response must be a JSON object", stripped_response, json_start)
        return parsed

    def get_formatted_commands(self) -> str:
        lines = []
        commands = self.app.command_handler.get_commands()
        for name, handler in commands.items():
            doc = handler.__doc__ if handler.__doc__ else "No description available."
            if "Router:Ignore" in doc:
                continue
            lines.append(f"- `{name}`: {doc}")
        return "\n".join(lines)

    def get_formatted_tools(self) -> str:
        lines = []
        for tool, desc in agent_tools.tools_list.items():
            lines.append(f"- `{tool}`: {desc}")
        return "\n".join(lines)

    def record_user_request(self, user_input: str, router_turn_id: Optional[str] = None) -> str:
        """Persist the user's router request once for a routing turn."""
        if router_turn_id is None:
            router_turn_id = uuid4().hex

        for msg in self.thread.messages:
            metadata = msg.get("metadata", {})
            if (
                msg.get("role") == "user"
                and metadata.get("event") == "user_request"
                and metadata.get("router_turn_id") == router_turn_id
            ):
                return router_turn_id

        self.thread.add_user_message(
            f"**User Request**: {user_input}",
            metadata={
                "type": "router_event",
                "event": "user_request",
                "router_turn_id": router_turn_id,
            },
        )
        return router_turn_id

    def _is_turn_user_request(self, msg: Dict[str, Any], router_turn_id: Optional[str]) -> bool:
        if not router_turn_id:
            return False
        metadata = msg.get("metadata", {})
        return (
            msg.get("role") == "user"
            and metadata.get("event") == "user_request"
            and metadata.get("router_turn_id") == router_turn_id
        )

    async def interpret(
        self,
        user_input: str,
        worker_id: str,
        previous_tool_calls: List[ToolCall] = None,
        router_turn_id: Optional[str] = None,
    ) -> Optional[ToolCall]:
        """
        Interpret user input, decide on a command, or ask for clarification.
        Returns a ToolCall object to be executed, or None.
        """
        router_turn_id = self.record_user_request(user_input, router_turn_id)

        builder = MessageBuilder(self.app)
        # Use the agent's private message history
        if self.thread.messages:
            historical_messages = self.thread.messages
            if not previous_tool_calls:
                historical_messages = [
                    msg for msg in historical_messages if not self._is_turn_user_request(msg, router_turn_id)
                ]
            builder.add_historical_messages(historical_messages)

        # Build the prompt for the LLM
        select_action_prompt = PromptManager().load("router/select_command")
        select_action_prompt = select_action_prompt.replace("tools_list", self.get_formatted_tools())
        select_action_prompt = select_action_prompt.replace("commands_list", self.get_formatted_commands())
        builder.add_system_message(select_action_prompt)
        builder.add_project_summary()

        # The first iteration carries the request in the current prompt. Later
        # iterations rely on the persisted turn record and add observations only.
        if not previous_tool_calls:
            builder.append_to_user_section(user_input)
        if previous_tool_calls:
            call_summaries = "\n--- Previous Assistant Actions For This User Request ---\n"
            for tc in previous_tool_calls:
                call_summaries += f"Command Entered: {tc.formatted_cmd}\nCommand Results: {tc.result}\n"
            builder.append_to_user_section(call_summaries)

        builder.finalize_user_section()

        messages = builder.build()

        # Use a specific, fast model for this routing task
        router_model = self.app.profile_manager().get_model("intent_router")
        response_model = router_model
        response_text = await generate_llm_response(self.app, router_model, messages, task_id=worker_id)

        try:
            response_json = self.parse_router_json(response_text)
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(
                f"Failed to parse router LLM response - running salvage: {e}\nResponse:\n {response_text}"
            )
            self.app.ui.print_text(
                "Rephrasing response...",
                print_type=PrintType.ERROR,
            )

            # run a salvage
            salvage_builder = MessageBuilder(self.app)
            salvage_prompt = PromptManager().load("router/salvage_response")
            salvage_builder.add_system_message(salvage_prompt)
            salvage_builder.add_user_message(response_text)

            salvage_model = self.app.profile_manager().get_model("quick_reasoning")
            response_model = salvage_model
            response_text = await generate_llm_response(
                self.app, salvage_model, salvage_builder.build(), task_id=worker_id
            )

            try:
                response_json = self.parse_router_json(response_text)
            except (json.JSONDecodeError, KeyError) as e2:
                self.logger.error(f"Failed to parse router JSON response{e2}\nResponse:\n {response_text}\n")
                msg = "Sorry, I had issues parsing my response. Do you want to try again?"
                self.thread.add_response(msg, model=response_model)
                self.app.ui.print_text(msg, print_type=PrintType.ERROR)
                return None

        # Add the structured assistant response to history *after* successful parsing.
        # The content is the JSON string of the decision.
        self.thread.add_response(json.dumps(response_json, indent=2), model=response_model)

        decision = response_json.get("decision")

        if decision == "execute_action":
            action = response_json.get("action")
            if not action:
                self.logger.error(
                    f"Router decision was 'execute_action' but no action was provided. Response: {response_json}"
                )
                self.app.ui.print_text(
                    "I decided to execute an action, but encountered an error. Please try again.",
                    print_type=PrintType.ERROR,
                )
                return None
            action_type = action.get("type")
            final_command = bool(response_json.get("final_command", False))
            reasoning = response_json.get("reasoning", "")
            return ToolCall(
                action_type=action_type,
                command=action["name"],
                args=action["args"],
                reasoning=reasoning,
                has_next=not final_command,
            )
        if decision == "clarify":
            question = response_json.get("question")
            self.app.ui.print_text(f"Clarification needed: {question}", print_type=PrintType.LLM)
            return None  # Halts execution, waits for next user input
        if decision == "summary":
            try:
                summary = response_json.get("response", "")
                self.app.ui.print_text(summary, print_type=PrintType.LLM)
            except Exception:
                # parsing failed, just dump raw
                self.app.ui.print_text(response_json, print_type=PrintType.LLM)
            return None
        if decision == "chat":
            # The LLM decided this is just a chat message, not a command.
            # We can optionally have it return the chat response directly.
            chat_response = response_json.get("response")
            self.app.ui.print_text(chat_response, print_type=PrintType.LLM)
            return None

        return None
