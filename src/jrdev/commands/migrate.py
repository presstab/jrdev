import asyncio
import os
from typing import Any, List

from jrdev.file_operations import file_utils
from jrdev.ui.ui import PrintType


async def handle_migrate(app: Any, _args: List[str], _worker_id: str):
    """
    Router:Ignore
    Handle the /migrate command: migrate all data from 'jrdev/' to '.jrdev/'.
    """
    old_dir = os.path.join(os.getcwd(), "jrdev")
    new_dir = os.path.join(os.getcwd(), ".jrdev")

    if not os.path.isdir(old_dir):
        app.ui.print_text("No old 'jrdev/' directory found. Nothing to migrate.", PrintType.INFO)
        return

    app.ui.print_text("Starting migration from 'jrdev/' to '.jrdev/'...", PrintType.INFO)
    try:
        # This function should move/copy all files and subdirs, handle conflicts, and return a summary dict
        result = file_utils.migrate_jrdev_directory(old_dir, new_dir)
        migrated = result.get("migrated", [])
        skipped = result.get("skipped", [])
        errors = result.get("errors", [])

        if migrated:
            app.ui.print_text(f"Migrated files/directories: {', '.join(migrated)}", PrintType.SUCCESS)
        if skipped:
            app.ui.print_text(f"Skipped (already existed): {', '.join(skipped)}", PrintType.WARNING)
        if errors:
            app.ui.print_text(f"Errors during migration: {', '.join(errors)}", PrintType.ERROR)
        if not migrated and not errors:
            app.ui.print_text("Migration completed: nothing to migrate.", PrintType.INFO)
        else:
            app.ui.print_text("Migration completed.", PrintType.SUCCESS)

        # Notify user about restart and shutdown
        app.ui.print_text("", PrintType.INFO)  # Empty line for spacing
        app.ui.print_text("Please restart JrDev to complete the migration.", PrintType.WARNING)
        app.ui.print_text("Application will shutdown in 5 seconds...", PrintType.INFO)

        # Wait 5 seconds then shutdown
        await asyncio.sleep(5)
        await app.ui.signal_exit()

    except Exception as e:
        app.logger.error(f"Migration failed: {e}")
        app.ui.print_text(f"Migration failed: {e}", PrintType.ERROR)

        # Still shutdown even on error, as partial migration may have occurred
        app.ui.print_text("", PrintType.INFO)  # Empty line for spacing
        app.ui.print_text("Please restart JrDev to ensure proper operation.", PrintType.WARNING)
        app.ui.print_text("Application will shutdown in 5 seconds...", PrintType.INFO)

        await asyncio.sleep(5)
        await app.ui.signal_exit()
