import json
from typing import Any, Dict, List, Optional

from jrdev.agents import agent_tools
from jrdev.core.tool_call import ToolCall
from jrdev.file_operations.file_utils import cutoff_string
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

    def _get_formatted_commands(self) -> str:
        lines = []
        commands = self.app.command_handler.get_commands()
        for name, handler in commands.items():
            doc = handler.__doc__ if handler.__doc__ else "No description available."
            if "Router:Ignore" in doc:
                continue
            lines.append(f"- `{name}`: {doc}")
        return "\n".join(lines)

    def _get_formatted_tools(self) -> str:
        lines = []
        for tool, desc in agent_tools.tools_list.items():
            lines.append(f"- `{tool}`: {desc}")
        return "\n".join(lines)

    async def interpret(
        self, user_input: str, worker_id: str, previous_tool_calls: List[ToolCall] = None
    ) -> Optional[ToolCall]:
        """
        Interpret user input, decide on a command, or ask for clarification.
        Returns a ToolCall object to be executed, or None.
        """
        builder = MessageBuilder(self.app)
        # Use the agent's private message history
        if self.thread.messages:
            builder.add_historical_messages(self.thread.messages)

        # Build the prompt for the LLM
        select_action_prompt = PromptManager().load("router/select_command")
        select_action_prompt = select_action_prompt.replace("tools_list", self._get_formatted_tools())
        select_action_prompt = select_action_prompt.replace("commands_list", self._get_formatted_commands())
        builder.add_system_message(select_action_prompt)

        # Add the actual user request
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
        response_text = await generate_llm_response(self.app, router_model, messages, task_id=worker_id)

        # The user's input is part of the request, so add it to history.
        user_msg_needed = True
        for msg in self.thread.messages:
            if msg.get("role") == "user" and msg.get("content") == user_input:
                user_msg_needed = False
                break
        if user_msg_needed:
            self.thread.messages.append({"role": "user", "content": f"**User Request**: {user_input}"})

        try:
            json_content = cutoff_string(response_text, "```json", "```")
            response_json = json.loads(json_content)

            # Add the structured assistant response to history *after* successful parsing.
            # The content is the JSON string of the decision.
            self.thread.messages.append(
                {"role": "assistant", "content": json.dumps(response_json, indent=2)}
            )

            decision = response_json.get("decision")

            if decision == "execute_action":
                action = response_json.get("action")
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
                summary = response_json.get("response", "")
                self.app.ui.print_text(summary, print_type=PrintType.LLM)
                return None
            if decision == "chat":
                # The LLM decided this is just a chat message, not a command.
                # We can optionally have it return the chat response directly.
                chat_response = response_json.get("response")
                self.app.ui.print_text(chat_response, print_type=PrintType.LLM)
                return None
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse router LLM response: {e}\nResponse:\n {response_text}")
            self.app.ui.print_text(
                "Sorry, I had trouble understanding that. Please try rephrasing or use a direct /command.",
                print_type=PrintType.ERROR,
            )
            return None

        return None
