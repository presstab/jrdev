#!/usr/bin/env python3

"""
Code command implementation for the JrDev application.
"""

from asyncio import CancelledError
import traceback
from typing import Any, List

from jrdev.agents.code_agent import CodeAgent
from jrdev.core.exceptions import CodeTaskCancelled
from jrdev.ui.ui import PrintType


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
    code_processor = CodeAgent(app, worker_id)
    try:
        await code_processor.process(message)
    except CodeTaskCancelled:
        app.ui.print_text("Code Task Cancelled")
    except CancelledError:
        app.ui.print_text("Worker Cancelled")
        raise
    except Exception as e:
        app.logger.error(f"Error in CodeAgent: {type(e)}{str(e)}\n{traceback.format_exc()}")
        app.ui.print_text(f"Error in CodeAgent: {type(e)}{str(e)}")
