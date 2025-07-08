#!/usr/bin/env python3

"""
Code command implementation for the JrDev application.
"""

from asyncio import CancelledError
import traceback
from typing import Any, List
import copy

from jrdev.agents.code_agent import CodeAgent
from jrdev.clients.token_client import report_token_usage
from jrdev.core.exceptions import CodeTaskCancelled
from jrdev.ui.ui import PrintType
from jrdev.core.usage import get_instance

async def handle_code(app: Any, args: List[str], worker_id: str) -> None:
    """
    Initiates an AI-driven, multi-step code generation or modification task.

    The AI agent will analyze the request, ask for relevant files to read,
    create a step-by-step plan, and then execute the plan by applying code
    changes. The user can review and approve changes at various stages.

    Usage:
      /code <your_detailed_request>

    Example:
      /code "Refactor the login function in auth.py to use async/await."
    """
    if len(args) < 2:
        app.ui.print_text("Usage: /code <message>", print_type=PrintType.ERROR)
        return
    message = " ".join(args[1:])
    
    usage_instance = get_instance()
    before_usage = copy.deepcopy(await usage_instance.get_usage())
    
    app.logger.debug(f"Before usage: {before_usage}")
    app.ui.print_text(f"DEBUG: Before usage: {before_usage}", print_type=PrintType.INFO)

    code_processor = CodeAgent(app, worker_id)
    try:

        await code_processor.process(message)
        after_usage = await usage_instance.get_usage()

        for model, usage in after_usage.items():
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]

            if model in before_usage:
                before_input = before_usage[model].get("input_tokens", 0)
                before_output = before_usage[model].get("output_tokens", 0)
                input_tokens -= before_input
                output_tokens -= before_output

            total_tokens = input_tokens + output_tokens
            if input_tokens > 0 or output_tokens > 0:
                try:
                    await report_token_usage(app, model, total_tokens)
                    app.ui.print_text(f"Successfully reported tokens for {model}", print_type=PrintType.SUCCESS)
                except Exception as report_error:
                    app.logger.error(f"Failed to report token usage for {model}: {report_error}")
                    app.ui.print_text(f"Failed to report tokens for {model}: {report_error}", print_type=PrintType.ERROR)
            else:
                app.ui.print_text(f" No tokens to report for {model} (delta: {total_tokens})", print_type=PrintType.INFO)

    except CodeTaskCancelled:
        app.ui.print_text("Code Task Cancelled")
    except CancelledError:
        app.ui.print_text("Worker Cancelled")
        raise
    except Exception as e:
        app.logger.error(f"Error in CodeAgent: {type(e)}{str(e)}\n{traceback.format_exc()}")
        app.ui.print_text(f"Error in CodeAgent: {type(e)}{str(e)}")
