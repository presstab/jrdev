from __future__ import annotations

from typing import Any, List, Optional

from jrdev.agents import agent_tools
from jrdev.core.commands import Command
from jrdev.core.tool_call import ToolCall
from jrdev.ui.ui import PrintType


class InputHandler:
    """Coordinates the agentic routing loop for free-form user input.

    The handler owns orchestration concerns such as invoking the router agent,
    executing resulting tool calls, relaying user feedback through the UI, and
    persisting conversational context. Decision making remains the
    responsibility of the router agent; this class simply delegates to it and
    executes the returned actions against the rest of the application.
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self._restricted_commands = {"/init", "/migrate", "/keys"}

    async def route(self, user_input: str, worker_id: Optional[str] = None) -> Optional[str]:
        """Interpret and execute user input via the router agent.

        Args:
            user_input: Raw input provided by the end user.
            worker_id: Optional identifier used for async task correlation.

        Returns:
            The last tool or command result surfaced back to the user, or
            ``None`` if the agent decided the conversation should end without
            executing an action.

        Side Effects:
            * Streams progress messages through ``app.ui``.
            * Mutates the router agent's conversation thread with action
              results, providing context for subsequent iterations.
            * May execute application commands or agent tools, depending on the
              router's decisions.
        """

        agent = getattr(self.app, "router_agent", None)
        if agent is None:
            self.app.logger.warning("Router agent not initialized; skipping natural language routing.")
            return None

        self.app.ui.print_text(
            "Interpreting your request...\n",
            print_type=PrintType.PROCESSING,
        )

        calls_made: List[ToolCall] = []
        last_result: Optional[str] = None
        max_iterations = max(1, self.app.user_settings.max_router_iterations)
        hit_iteration_limit = True

        for _ in range(max_iterations):
            tool_call = await agent.interpret(user_input, worker_id, calls_made)
            if not tool_call:
                hit_iteration_limit = False
                break

            try:
                self._announce_tool_call(tool_call)
                if tool_call.action_type == "command":
                    await self._execute_command(agent, tool_call, worker_id)
                elif tool_call.action_type == "tool":
                    await self._execute_tool(agent, tool_call)
                else:
                    self.app.logger.error("Unknown tool call action type '%s'.", tool_call.action_type)
                    hit_iteration_limit = False
                    break
            except Exception:  # pragma: no cover - defensive logging path
                self.app.logger.error(
                    "Unhandled error while processing tool call '%s'.",
                    tool_call.formatted_cmd,
                    exc_info=True,
                )
                self.app.ui.print_text(
                    "I hit an unexpected error while handling that request. Please try again.",
                    print_type=PrintType.ERROR,
                )
                hit_iteration_limit = False
                break

            if tool_call.result:
                last_result = tool_call.result

            if not tool_call.has_next:
                hit_iteration_limit = False
                break

            calls_made.append(tool_call)

        if hit_iteration_limit:
            self.app.ui.print_text(
                "My maximum command iterations have been hit for this request. Please reprompt to "
                "continue. You can adjust this using the /routeragent command",
                print_type=PrintType.ERROR,
            )

        return last_result

    def _announce_tool_call(self, tool_call: ToolCall) -> None:
        message = (
            f"Running command: {tool_call.formatted_cmd}\n"
            f"Command Purpose: {tool_call.reasoning}\n"
        )
        self.app.ui.print_text(message, print_type=PrintType.PROCESSING)

    async def _execute_command(
        self,
        agent: Any,
        tool_call: ToolCall,
        worker_id: Optional[str],
    ) -> None:
        command_to_execute = tool_call.formatted_cmd

        if tool_call.command in self._restricted_commands:
            error_message = (
                f"Error: Router Agent is restricted from using the {tool_call.command} command."
            )
            self.app.ui.print_text(error_message, PrintType.ERROR)
            tool_call.result = error_message
            self._append_thread_message(agent, error_message)
            tool_call.has_next = False
            return

        self.app.ui.start_capture()
        try:
            command = Command(command_to_execute, worker_id)
            await self.app.handle_command(command)
        finally:
            self.app.ui.end_capture()

        tool_call.result = self.app.ui.get_capture()
        self._append_thread_message(agent, tool_call.result)

        if command_to_execute.startswith("/code"):
            tool_call.has_next = False

    async def _execute_tool(self, agent: Any, tool_call: ToolCall) -> None:
        result = await self._run_tool(tool_call)

        tool_call.result = result
        self._append_thread_message(agent, result)

    async def _run_tool(self, tool_call: ToolCall) -> str:
        try:
            if tool_call.command not in agent_tools.tools_list:
                return f"Error: Tool '{tool_call.command}' does not exist."
            if tool_call.command == "read_files":
                return agent_tools.read_files(tool_call.args)
            if tool_call.command == "get_file_tree":
                return agent_tools.get_file_tree()
            if tool_call.command == "write_file":
                if not tool_call.args:
                    return "Error: write_file requires a filename and content."
                filename = tool_call.args[0]
                content = " ".join(tool_call.args[1:])
                return await agent_tools.write_file(self.app, filename, content)
            if tool_call.command == "web_search":
                return agent_tools.web_search(tool_call.args)
            if tool_call.command == "web_scrape_url":
                return await agent_tools.web_scrape_url(tool_call.args)
            if tool_call.command == "get_indexed_files_context":
                return agent_tools.get_indexed_files_context(self.app, tool_call.args)
            if tool_call.command == "terminal":
                command_str = " ".join(tool_call.args)
                confirmed = await self.app.ui.prompt_for_command_confirmation(command_str)
                if confirmed:
                    return agent_tools.terminal(tool_call.args)
                self.app.ui.print_text("Command execution cancelled.", PrintType.INFO)
                return "Terminal command request REJECTED by user."
        except Exception as exc:  # pragma: no cover - defensive logging path
            error_message = f"Error executing tool '{tool_call.command}': {exc}"
            self.app.logger.error(error_message, exc_info=True)
            return error_message

        return f"Tool '{tool_call.command}' is not implemented."

    def _append_thread_message(self, agent: Any, content: Optional[str]) -> None:
        if not content or not hasattr(agent, "thread"):
            return
        thread = agent.thread
        if thread is None:
            return
        thread.messages.append({"role": "assistant", "content": content})
