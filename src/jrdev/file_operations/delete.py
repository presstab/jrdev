import logging

from jrdev.file_operations.find_function import find_function
from jrdev.string_utils import find_code_snippet
from jrdev.ui.ui import terminal_print, PrintType

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
    logger.info("processing delete operation")

    target = change.get("target")
    if target is None or not isinstance(target, dict):
        raise KeyError("target")

    filepath = change.get("filename")
    if filepath is None:
        raise KeyError("filename")

    target_function = target.get("function")
    if target_function:
        # function deletion requested
        matched_function = find_function(target_function, filepath)
        if matched_function is None:
            raise ValueError("function")
        new_lines = lines[:matched_function["start_line"]-1] + lines[matched_function["end_line"]:]
        logger.info(f"Removed function: {matched_function}\n New Lines:\n{new_lines} ")
        return new_lines

    snippet = target.get("snippet")
    if snippet:
        start_idx, end_idx = find_code_snippet(lines, snippet)
        if start_idx != -1:
            del lines[start_idx:end_idx]
            return lines

    # Convert 1-indexed line numbers to 0-indexed indices
    start_idx = change["start_line"] - 1
    end_idx = change["end_line"]

    message = f"Deleting content from line {change['start_line']} to {change['end_line']} in {change['filename']}"
    terminal_print(message, PrintType.INFO)
    logger.info(message)

    return lines[:start_idx] + lines[end_idx:]
