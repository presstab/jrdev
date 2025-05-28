import logging
import os
from typing import Tuple, Optional

from jrdev.file_operations.find_function import find_function
from jrdev.utils.string_utils import find_code_snippet
from jrdev.ui.ui import PrintType

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
    logger.info(message)

    return lines[:start_idx] + lines[end_idx:]


async def delete_with_confirmation(app, filepath: str) -> Tuple[str, Optional[str]]:
    """
    Delete a file with user confirmation.
    
    Args:
        app: The application instance
        filepath: Path to the file to delete
        
    Returns:
        Tuple of (response, message):
            - response: 'yes' if file was deleted, 'no' if deletion was cancelled
            - message: Always None for this operation
    """
    try:
        # Check if file exists
        if not os.path.exists(filepath):
            app.ui.print_text(f"File not found: {filepath}", PrintType.WARNING)
            logger.warning(f"Attempted to delete non-existent file: {filepath}")
            return 'no', None
        
        # Prompt user for deletion confirmation
        confirmed = await app.ui.prompt_for_deletion(filepath)
        
        if confirmed:
            try:
                # Perform the actual file deletion
                os.remove(filepath)
                app.ui.print_text(f"File deleted: {filepath}", PrintType.SUCCESS)
                logger.info(f"File successfully deleted: {filepath}")
                return 'yes', None
            except OSError as e:
                error_msg = f"Failed to delete file {filepath}: {e}"
                app.ui.print_text(error_msg, PrintType.ERROR)
                logger.error(f"Error deleting file {filepath}: {e}", exc_info=True)
                return 'no', None
        else:
            app.ui.print_text(f"File deletion cancelled: {filepath}", PrintType.INFO)
            logger.info(f"File deletion cancelled by user: {filepath}")
            return 'no', None
            
    except Exception as e:
        error_msg = f"Unexpected error during file deletion: {e}"
        app.ui.print_text(error_msg, PrintType.ERROR)
        logger.error(f"Unexpected error deleting file {filepath}: {e}", exc_info=True)
        return 'no', None
