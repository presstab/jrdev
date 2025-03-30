#!/usr/bin/env python3

"""
Code command implementation for the JrDev terminal.
"""

from typing import Any, List

from jrdev.ui.ui import terminal_print, PrintType
from jrdev.code_processor import CodeProcessor


async def handle_code(terminal: Any, args: List[str]) -> None:
    if len(args) < 2:
        terminal_print("Usage: /code <message>", print_type=PrintType.ERROR)
        return
    message = " ".join(args[1:])
    code_processor = CodeProcessor(terminal)
    await code_processor.process(message)
