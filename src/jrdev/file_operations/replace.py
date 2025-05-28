import logging
import re

from jrdev.file_operations.find_function import find_function
from jrdev.utils.string_utils import find_code_snippet

# Get the global logger instance
logger = logging.getLogger("jrdev")


def process_replace_operation(lines, change, filepath):
    """
    Process a REPLACE operation to replace content in a file.

    Args:
        lines: List of file lines to modify
        change: The change specification containing REPLACE operation details
        filepath: Path to the file being modified

    Returns:
        Updated list of lines
    """
    logger.info("process_replace_operation")
    # Extract replacement details
    target_type = change.get("target_type", "")
    target_ref = change.get("target_reference", {})


    error_detail = ""
    # Check for code_snippet first, as it can be used with any target_type
    if "target_reference" in change and "code_snippet" in change["target_reference"]:
        # Handle code_snippet replacement regardless of target_type
        return replace_code_snippet(lines, change, filepath)
    elif target_type == "SIGNATURE" and "function_name" in target_ref:
        return replace_function_signature(lines, change, filepath)
    elif target_type == "FUNCTION" and "function_name" in target_ref:
        return replace_function_implementation(lines, change, filepath)
    elif target_type == "BLOCK":
        logger.info("type BLOCK")
        if "function_name" not in target_ref:
            error_detail = "function_name not in target_type"
        elif "start_marker" not in target_ref:
            error_detail = "start_marker not in target_type"
        elif "end_marker" not in target_ref:
            error_detail = "end_marker not in target_type"
        else:
            return replace_code_block(lines, change, filepath)

    message = f"Warning: REPLACE operation error: {error_detail}\n {change}"
    logger.warning(message)

    return lines


def replace_code_snippet(lines, change, filepath):
    """
    Replace a code snippet anywhere in the file.

    Args:
        lines: List of file lines
        change: The change specification containing target_reference.code_snippet and new_content
        filepath: Path to the file being modified

    Returns:
        List: Updated list of lines
    """
    target_ref = change["target_reference"]
    code_snippet = target_ref.get("code_snippet", "")
    new_content = change["new_content"]

    if not code_snippet:
        message = f"Warning: Missing code_snippet in target_reference: {change}"
        logger.warning(message)
        return lines

    # Find the code snippet
    start_idx, end_idx = find_code_snippet(lines, code_snippet)

    if start_idx == -1 or end_idx == -1:
        message = f"Warning: Could not find code snippet in {filepath}"
        logger.warning(message)
        return lines

    # Get indentation from the first line of the snippet
    indentation = ""
    if lines[start_idx].strip():
        # Calculate leading whitespace
        indentation = lines[start_idx][:len(lines[start_idx]) - len(lines[start_idx].lstrip())]

    # Prepare the new content with proper line endings and indentation
    new_lines = []
    content_lines = new_content.splitlines()
    for i, line in enumerate(content_lines):
        # Process each line based on content and position
        if not line.strip():
            new_lines.append("\n")
        else:
            # Respect existing indentation in the line
            if line.startswith(" ") or line.startswith("\t"):
                new_lines.append(line + "\n")
            else:
                new_lines.append(indentation + line + "\n")

        # If this line is not the last line and is followed by an empty line,
        # make sure we preserve the empty line
        if i < len(content_lines) - 1 and not content_lines[i + 1].strip():
            new_lines.append("\n")

    # Replace the snippet
    lines = lines[:start_idx] + new_lines + lines[end_idx:]

    message = f"Replaced code snippet in {filepath}"
    logger.info(message)

    return lines


def replace_function_signature(lines, change, filepath):
    """
    Replace a function signature in file lines.

    Args:
        lines: List of file lines
        change: The change specification containing target_reference.function_name and new_content
        filepath: Path to the file being modified

    Returns:
        List: Updated list of lines
    """
    function_name = change["target_reference"]["function_name"]
    new_content = change["new_content"]

    line_idx = find_function_signature(lines, function_name)
    if line_idx >= 0:
        # Get indentation from the original line
        indentation = ""
        if lines[line_idx].strip():
            # Calculate leading whitespace
            indentation = lines[line_idx][:len(lines[line_idx]) - len(lines[line_idx].lstrip())]

        # Apply indentation to the new content if it doesn't already have it
        if not new_content.startswith(" ") and not new_content.startswith("\t") and indentation:
            new_content = indentation + new_content

        # Replace the entire line with the new signature
        lines[line_idx] = new_content + "\n" if not new_content.endswith("\n") else new_content

        message = f"Replaced signature for function '{function_name}' in {filepath}"
        logger.info(message)
    else:
        message = f"Warning: Could not find signature for function '{function_name}' in {filepath}"
        logger.warning(message)

    return lines


def find_function_signature(lines, function_name):
    """
    Find a function signature in file lines based on function name.

    Args:
        lines: List of file lines
        function_name: Name of the function to find

    Returns:
        int: Index of the line containing the function signature, or -1 if not found
    """
    for i, line in enumerate(lines):
        # Use a pattern to match the function name with possible return type and parameters
        pattern = r'\b' + re.escape(function_name) + r'\s*\(.*\)'
        if re.search(pattern, line):
            return i
    return -1

def replace_function_implementation(lines, change, filepath):
    """
    Replace a complete function implementation in file lines.

    Args:
        lines: List of file lines
        change: The change specification containing target_reference.function_name and new_content
        filepath: Path to the file being modified

    Returns:
        List: Updated list of lines
    """
    function_name = change["target_reference"]["function_name"]
    new_content = change["new_content"]

    # Find matching function
    matched_function = find_function(function_name, filepath)
    if matched_function is None:
        raise LookupError(f"{function_name}")

    # Get the start and end line indexes (convert from 1-indexed to 0-indexed)
    start_idx = matched_function["start_line"] - 1
    end_idx = matched_function["end_line"]

    # Get indentation from the original function
    indentation = ""
    if lines[start_idx].strip():
        # Calculate leading whitespace
        indentation = lines[start_idx][:len(lines[start_idx]) - len(lines[start_idx].lstrip())]

    # Prepare the new function implementation with proper line endings and indentation
    new_lines = []
    for i, line in enumerate(new_content.splitlines()):
        # Skip indentation for blank lines
        if not line.strip():
            new_lines.append("\n")
        else:
            # First line or already indented lines keep their formatting
            if i == 0 or line.startswith(" ") or line.startswith("\t"):
                new_lines.append(line + "\n")
            else:
                # Apply indentation to content lines
                new_lines.append(indentation + line + "\n")

    # Replace the entire function
    lines = lines[:start_idx] + new_lines + lines[end_idx:]

    message = f"Replaced function '{function_name}' in {filepath}"
    logger.info(message)

    return lines


def replace_code_block(lines, change, filepath):
    """
    Replace a code block within a function.

    Args:
        lines: List of file lines
        change: The change specification containing target_reference details and new_content
        filepath: Path to the file being modified

    Returns:
        List: Updated list of lines
    """
    target_ref = change["target_reference"]
    function_name = target_ref.get("function_name")
    start_marker = target_ref.get("start_marker")
    end_marker = target_ref.get("end_marker")
    new_content = change["new_content"]

    if function_name is None or start_marker is None or end_marker is None:
        raise Exception(f"Missing required target_reference fields for BLOCK replacement: {change}")

    # Find matching function
    matched_function = find_function(function_name, filepath)
    if matched_function is None:
        raise LookupError(f"{function_name}")

    # Get the function bounds
    func_start = matched_function["start_line"] - 1
    func_end = matched_function["end_line"]

    # Find the block within the function
    block_start = None
    block_end = None

    for i in range(func_start, func_end):
        if start_marker in lines[i]:
            block_start = i
        if end_marker in lines[i] and block_start is not None:
            block_end = i + 1
            break

    if block_start is None or block_end is None:
        message = f"Warning: Could not find block in function '{function_name}' in {filepath}"
        logger.warning(message)
        return lines

    # Get indentation from the first line of the block
    indentation = ""
    if lines[block_start].strip():
        # Calculate leading whitespace
        indentation = lines[block_start][:len(lines[block_start]) - len(lines[block_start].lstrip())]

    # Prepare the new block with proper line endings and indentation
    new_lines = []
    for line in new_content.splitlines():
        # Skip indentation for blank lines
        if not line.strip():
            new_lines.append("\n")
        else:
            # Respect existing indentation in the line
            if line.startswith(" ") or line.startswith("\t"):
                new_lines.append(line + "\n")
            else:
                new_lines.append(indentation + line + "\n")

    # Replace the block
    lines = lines[:block_start] + new_lines + lines[block_end:]

    message = f"Replaced block in function '{function_name}' in {filepath}"
    logger.info(message)

    return lines
