import re
import os
import glob
from difflib import SequenceMatcher
import logging

from jrdev.ui.ui import terminal_print, PrintType
from jrdev.languages import get_language_for_file

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
    start_idx = change["start_line"] - 1
    # For add operations, end_idx is the same as start_idx
    end_idx = start_idx

    new_content = change["new_content"]
    new_content = new_content.replace("\\n", "\n").replace("\\\"", "\"")

    # Check if this is a FUNCTION sub_type that needs special handling
    if "sub_type" in change and change["sub_type"] == "FUNCTION":
        lines, start_idx, end_idx, new_lines = process_function_subtype(lines, new_content, filename)
    else:
        message = f"Adding content at line {change['start_line']} in {filename}"
        terminal_print(message, PrintType.INFO)
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
    # For function sub-type, add to the end of the file with a blank line separation
    start_idx = len(lines)
    end_idx = len(lines)

    # Ensure there's exactly one blank line between functions
    lines_copy = lines.copy()
    if lines_copy:
        # First, check if file already ends with blank lines
        blank_line_count = 0
        for i in range(len(lines_copy) - 1, -1, -1):
            if not lines_copy[i].strip():
                blank_line_count += 1
            else:
                break

        # Remove all blank lines
        while blank_line_count > 0:
            lines_copy.pop()
            blank_line_count -= 1

        # Add exactly one blank line between functions
        lines_copy.append("\n")
        lines_copy.append("\n")

    message = f"Adding function to the end of {filename}"
    terminal_print(message, PrintType.INFO)
    logger.info(message)

    # Prepare the new content
    new_lines = [
        line + ("\n" if not line.endswith("\n") else "")
        for line in new_content.split("\n")
    ]

    return lines_copy, start_idx, end_idx, new_lines