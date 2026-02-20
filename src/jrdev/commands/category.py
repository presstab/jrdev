import argparse
from typing import Any, List
import os

from jrdev.ui.ui import PrintType
from jrdev.messages.thread import THREADS_DIR

async def handle_category(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Manage categories for message threads.

    Usage:
      /category create <name>
    """
    if len(args) < 3 or args[1] != "create":
        app.ui.print_text("Usage: /category create <name>", PrintType.ERROR)
        return

    category_name = args[2]

    # Validate name (no slashes, dots, etc)
    if not category_name.replace('_', '').replace('-', '').isalnum():
         app.ui.print_text("Error: Category name must be alphanumeric (with underscores or hyphens).", PrintType.ERROR)
         return

    cat_dir = os.path.join(THREADS_DIR, category_name)
    try:
        os.makedirs(cat_dir, exist_ok=True)
        app.ui.print_text(f"Category '{category_name}' created.", PrintType.SUCCESS)
    except OSError as e:
        app.ui.print_text(f"Error creating category: {e}", PrintType.ERROR)
