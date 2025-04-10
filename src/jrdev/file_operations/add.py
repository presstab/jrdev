import logging

from jrdev.file_operations.insert import process_insert_after_changes

# Get the global logger instance
logger = logging.getLogger("jrdev")


def process_add_operation(lines, change, filename):
    """
    Process an ADD operation to insert new content at a specific line.

    Args:
        lines: List of file lines
        change: The change specification
        filename: Name of the file being modified

    Returns:
        Updated list of lines
    """
    # Convert 1-indexed line numbers to 0-indexed indices
    start_idx = 0
    # For add operations, end_idx is the same as start_idx
    end_idx = start_idx

    new_content = change["new_content"]

    # right now every ADD should have insert_location in it
    if change.get("insert_location") is not None:
        return process_insert_after_changes(lines, change, filename)

    logger.info("process_add_operation default")
    message = f"Adding content at line {change['start_line']} in {filename}"
    logger.info(message)

    # Prepare the new content and insert it
    new_lines = [
        line + ("\n" if not line.endswith("\n") else "")
        for line in new_content.split("\n")
    ]
    return lines[:start_idx] + new_lines + lines[end_idx:]


def process_function_subtype(lines, new_content, filename):
    """
    Process a FUNCTION sub_type change by adding it to the end of the file.

    Args:
        lines: List of file lines
        new_content: Content to add
        filename: Name of the file being modified

    Returns:
        Tuple of (start_idx, end_idx, new_content_lines)
    """

    logger.info(f"Adding function to the end of {filename}")

    # Ensure there's exactly one blank line between functions
    lines_copy = lines.copy()
    last_line = lines_copy[-1]
    if last_line != "\n":
        lines_copy.append("\n")

    lines_copy.extend(new_content)
    return lines_copy
