#!/usr/bin/env python3

"""
Code command implementation for the JrDev application.
"""

from typing import Any, List

from jrdev.ui.ui import PrintType
from jrdev.code_processor import CodeProcessor


async def handle_code(app: Any, args: List[str], worker_id: str) -> None:
    if len(args) < 2:
        app.ui.print_text("Usage: /code <message>", print_type=PrintType.ERROR)
        return
    message = " ".join(args[1:])
    code_processor = CodeProcessor(app)
    await code_processor.process(message)
