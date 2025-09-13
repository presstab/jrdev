import asyncio
from typing import Any, List, Optional

from jrdev.agents import agent_tools
from jrdev.agents.research_agent import ResearchAgent
from jrdev.core.tool_call import ToolCall
from jrdev.ui.ui import PrintType


async def handle_research(app: Any, args: List[str], worker_id: str, chat_thread_id: Optional[str] = None) -> None:
    """
    Initiates a research agent to investigate a topic using web search and scraping tools.
    Usage: /research <your query>
    If chat_thread_id is provided, it runs in the context of that chat.
    """
    if len(args) < 2:
        if not chat_thread_id:  # Only show usage error for command line
            app.ui.print_text("Usage: /research <your query>", print_type=PrintType.ERROR)
        return

    user_input = " ".join(args[1:])

    # Determine the research thread and initial output
    if chat_thread_id:
        research_thread = app.get_thread(chat_thread_id)
    else:
        app.ui.print_text(f'Starting research for: "{user_input}"\n', print_type=PrintType.INFO)
        new_thread_id = app.create_thread(meta_data={"type": "research", "topic": user_input})
        research_thread = app.get_thread(new_thread_id)

    # Initialize the research agent
    research_agent = ResearchAgent(app, research_thread)

    calls_made: List[ToolCall] = []
    max_iter = app.user_settings.max_router_iterations
    i = 0
    summary = None

    while i < max_iter:
        i += 1
        await asyncio.sleep(0.01)

        decision = await research_agent.interpret(user_input, worker_id, calls_made)

        if not decision:
            msg = "Research task concluded due to an agent error."
            if chat_thread_id:
                app.ui.stream_chunk(chat_thread_id, msg)
                app.ui.chat_thread_update(chat_thread_id)
            else:
                app.ui.print_text(msg, print_type=PrintType.ERROR)
            break

        decision_type = decision.get("type")
        data = decision.get("data")

        if decision_type == "summary":
            summary = data
            break

        if decision_type == "tool_call":
            tool_call: ToolCall = data
            command_to_execute = tool_call.formatted_cmd

            if not chat_thread_id:  # Only print progress to terminal
                app.ui.print_text(f"Running tool: {command_to_execute}\nPurpose: {tool_call.reasoning}\n",
                                  print_type=PrintType.PROCESSING)

            try:
                if tool_call.command == "web_search":
                    tool_call.result = agent_tools.web_search(tool_call.args)
                elif tool_call.command == "web_scrape_url":
                    tool_call.result = await agent_tools.web_scrape_url(tool_call.args)
                else:
                    error_msg = f"Error: Research Agent tried to use an unauthorized tool: '{tool_call.command}'"
                    if not chat_thread_id:
                        app.ui.print_text(error_msg, PrintType.ERROR)
                    tool_call.result = error_msg
            except Exception as e:
                error_message = f"Error executing tool '{tool_call.command}': {str(e)}"
                app.logger.error(f"Tool execution failed: {error_message}", exc_info=True)
                tool_call.result = error_message

            calls_made.append(tool_call)
        else:
            msg = f"Unknown decision type from research agent: {decision_type}"
            if chat_thread_id:
                app.ui.stream_chunk(chat_thread_id, msg)
                app.ui.chat_thread_update(chat_thread_id)
            else:
                app.ui.print_text(msg, print_type=PrintType.ERROR)
            break

    if summary:
        if chat_thread_id:
            # The agent adds the summary to the thread history. We stream it to the UI.
            app.ui.stream_chunk(chat_thread_id, summary)
            app.ui.chat_thread_update(chat_thread_id)
        else:
            # For command-line, print the summary to the terminal.
            app.ui.print_text("\n--- Research Summary ---\n", print_type=PrintType.SUCCESS)
            app.ui.print_text(summary, print_type=PrintType.INFO)

    if i >= max_iter and not summary:
        msg = "Research agent hit maximum iterations for this request. You can adjust this limit using the /routeragent command."
        if chat_thread_id:
            app.ui.stream_chunk(chat_thread_id, msg)
            app.ui.chat_thread_update(chat_thread_id)
        else:
            app.ui.print_text(msg, print_type=PrintType.WARNING)
