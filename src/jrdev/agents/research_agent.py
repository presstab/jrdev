import json
from typing import Any, Dict, List, Optional

from jrdev.core.tool_call import ToolCall
from jrdev.file_operations.file_utils import cutoff_string
from jrdev.messages.thread import MessageThread
from jrdev.messages.message_builder import MessageBuilder
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class ResearchAgent:
    ALLOWED_TOOLS = {"web_search", "web_scrape_url"}

    def __init__(self, app: Any, thread: MessageThread):
        self.app = app
        self.logger = app.logger
        self.thread = thread

    async def interpret(
        self, user_input: str, worker_id: str, previous_tool_calls: List[ToolCall] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Interpret user input for research, decide on a tool to use, or provide a summary.
        Returns a dictionary representing the LLM's decision.
        """
        builder = MessageBuilder(self.app)
        # Use the agent's private message history
        if self.thread.messages:
            builder.add_historical_messages(self.thread.messages)

        # Build the prompt for the LLM
        research_prompt = PromptManager().load("researcher/research_prompt")
        builder.add_system_message(research_prompt)

        # Add the actual user request
        builder.append_to_user_section(f"User Research Request: {user_input}")
        if previous_tool_calls:
            call_summaries = "\n--- Previous Research Actions For This Request ---\n"
            for tc in previous_tool_calls:
                call_summaries += f"Tool Used: {tc.formatted_cmd}\nTool Results: {tc.result}\n"
            builder.append_to_user_section(call_summaries)

        builder.finalize_user_section()

        messages = builder.build()

        # The user's input is part of the request, so add it to history.
        if not previous_tool_calls:
            self.thread.messages.append({"role": "user", "content": f"**Researching**: {user_input}"})

        # Use a specific model for this task
        research_model = self.app.state.model
        response_text = await generate_llm_response(self.app, research_model, messages, task_id=worker_id)

        json_content = ""
        try:
            json_content = cutoff_string(response_text, "```json", "```")
            response_json = json.loads(json_content)
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(
                f"Failed to parse research agent LLM response: {e}\nResponse:\n {response_text}\nRaw:\n{json_content}")
            self.app.ui.print_text(
                "Research agent had an issue parsing its own response. This may be a temporary issue. Aborting research task.",
                print_type=PrintType.ERROR,
            )
            return None

        # Add the structured assistant response to history *after* successful parsing.
        self.thread.messages.append(
            {"role": "assistant", "content": json.dumps(response_json, indent=2)}
        )

        decision = response_json.get("decision")

        if decision == "execute_action":
            action = response_json.get("action")
            if not action:
                self.logger.error(f"Research agent decision was 'execute_action' but no action was provided. Response: {response_json}")
                self.app.ui.print_text("Research agent decided to execute an action, but encountered an error. Aborting.", print_type=PrintType.ERROR)
                return None

            tool_name = action.get("name")
            if tool_name not in self.ALLOWED_TOOLS:
                self.logger.error(
                    f"Research agent attempted to use an unauthorized tool: {tool_name}. Allowed tools are: {self.ALLOWED_TOOLS}"
                )
                self.app.ui.print_text(
                    f"Research agent tried to use an unauthorized tool '{tool_name}'. Aborting research task.",
                    print_type=PrintType.ERROR,
                )
                return None

            tool_call = ToolCall(
                action_type="tool",
                command=tool_name,
                args=action["args"],
                reasoning=response_json.get("reasoning", ""),
                has_next=True,  # Research agent always has a next step until it summarizes
            )
            return {"type": "tool_call", "data": tool_call}

        if decision == "summary":
            summary = response_json.get("response", "")
            # Add summary to thread as final assistant message
            self.thread.messages.append({"role": "assistant", "content": summary})
            return {"type": "summary", "data": summary}

        self.logger.error(f"Research agent returned an unknown decision: {decision}. Aborting.")
        self.app.ui.print_text(f"Research agent returned an unknown decision: {decision}. Aborting.", print_type=PrintType.ERROR)
        return None
