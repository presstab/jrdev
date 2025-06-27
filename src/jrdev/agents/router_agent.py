import json
from typing import Any, Optional

from jrdev.file_operations.file_utils import cutoff_string
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class CommandInterpretationAgent:
    def __init__(self, app: Any):
        self.app = app
        self.logger = app.logger
        # Use the dedicated system thread for conversation history
        self.thread = self.app.state.get_thread(self.app.state.router_thread_id)

    def _get_available_commands_prompt(self) -> str:
        """Generates a formatted string of available commands for the LLM."""
        # This is key: we dynamically generate the tool list!
        # For this to be effective, command handlers should have good docstrings.
        commands = self.app.command_handler.get_commands()
        prompt_lines = ["Here are the available tools/commands you can use:"]
        for name, handler in commands.items():
            # We can improve this by parsing argparse help text from each command file
            # For now, a simple docstring is a great start.
            doc = handler.__doc__ if handler.__doc__ else "No description available."
            prompt_lines.append(f"- `{name}`: {doc}")
        return "\n".join(prompt_lines)

    async def interpret(self, user_input: str, worker_id: str) -> Optional[str]:
        """
        Interpret user input, decide on a command, or ask for clarification.
        Returns a string command to be executed, or None.
        """
        builder = MessageBuilder(self.app)
        # Use the agent's private message history
        if self.thread.messages:
            builder.add_historical_messages(self.thread.messages)

        # Build the prompt for the LLM
        builder.load_system_prompt("router/select_command")

        # Add dynamic command list
        command_list_prompt = self._get_available_commands_prompt()
        self.app.logger.info(f"*** commands:\n {command_list_prompt}")
        builder.append_to_user_section(command_list_prompt)

        # Add the actual user request
        builder.append_to_user_section(f"\n--- User Request ---\n{user_input}")
        builder.finalize_user_section()

        messages = builder.build()

        # Use a specific, fast model for this routing task
        router_model = self.app.profile_manager().get_model("quick_reasoning")
        response_text = await generate_llm_response(self.app, router_model, messages, task_id=worker_id)

        # Update the agent's private history
        self.thread.messages.append({"role": "user", "content": user_input})
        self.thread.messages.append({"role": "assistant", "content": response_text})
        self.thread.save()  # Persist the conversation

        try:
            json_content = cutoff_string(response_text, "```json", "```")
            response_json = json.loads(json_content)
            decision = response_json.get("decision")

            if decision == "execute_command":
                command = response_json.get("command")
                # Reconstruct the command string from parts
                full_command = f"{command['name']} {' '.join(command['args'])}"
                return full_command.strip()
            if decision == "clarify":
                question = response_json.get("question")
                self.app.ui.print_text(f"Clarification needed: {question}", print_type=PrintType.INFO)
                return None  # Halts execution, waits for next user input
            if decision == "chat":
                # The LLM decided this is just a chat message, not a command.
                # We can optionally have it return the chat response directly.
                chat_response = response_json.get("response")
                self.app.ui.print_text(chat_response, print_type=PrintType.LLM)

                # Add to the *user's* active thread, not the router's
                user_thread = self.app.get_current_thread()
                user_thread.messages.append({"role": "user", "content": user_input})
                user_thread.messages.append({"role": "assistant", "content": chat_response})
                user_thread.save()
                return None
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse router LLM response: {e}\nResponse: {response_text}")
            self.app.ui.print_text(
                "Sorry, I had trouble understanding that. Please try rephrasing or use a direct /command.",
                print_type=PrintType.ERROR,
            )
            return None

        return None
