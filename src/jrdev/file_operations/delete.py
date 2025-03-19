import logging

from jrdev.ui import terminal_print, PrintType

# Get the global logger instance
logger = logging.getLogger("jrdev")

def process_delete_operation(lines, change):
    """
    Process a DELETE operation to remove content from specific lines.

    Args:
        lines: List of file lines
        change: The change specification

    Returns:
        Updated list of lines
    """
    # Convert 1-indexed line numbers to 0-indexed indices
    start_idx = change["start_line"] - 1
    end_idx = change["end_line"]

    message = f"Deleting content from line {change['start_line']} to {change['end_line']} in {change['filename']}"
    terminal_print(message, PrintType.INFO)
    logger.info(message)

    return lines[:start_idx] + lines[end_idx:]