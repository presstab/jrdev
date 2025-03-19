import logging
import re

from jrdev.ui import terminal_print, PrintType
from jrdev.languages import get_language_for_file
from jrdev.languages.utils import detect_language


# Get the global logger instance
logger = logging.getLogger("jrdev")


def process_insert_after_changes(lines, insert_after_changes, filepath):
    """
    Process changes based on insert_location object with various location options.

    Args:
        lines: List of file lines
        insert_after_changes: List of changes with insert_location directive
        filepath: Path to the file being modified

    Returns:
        Updated list of lines
    """
    for change in insert_after_changes:
        if "filename" not in change:
            raise Exception(f"filename not in change: {change}")
        if "new_content" not in change:
            raise Exception(f"new_content not in change: {change}")

        # Process with insert_location object
        if "insert_location" in change:
            location = change["insert_location"]

            # Handle all insert location types
            if "after_function" in location:
                # Copy the change and add insert_after_function for compatibility
                function_change = change.copy()
                function_change["insert_after_function"] = location["after_function"]
                insert_after_function(function_change, lines, filepath)
                continue

            elif "within_function" in location:
                insert_within_function(change, lines, filepath)
                continue

            elif "after_marker" in location:
                insert_after_marker(change, lines, filepath)
                continue

            elif "global" in location:
                insert_global(change, lines, filepath)
                continue

            # Handle the case for after_line (corrected to use after_marker instead)
            elif "after_line" in location:
                # Copy the change and create a new insert_location with after_marker
                terminal_print(f"Warning: SKIPPED CHANGED: 'after_line' is deprecated, use 'after_marker' instead",
                               PrintType.WARNING)
                continue

            else:
                raise Exception(f"Invalid insert_location, missing a valid location type: {change}")
        else:
            raise Exception(f"Missing insert_location in change: {change}")

    return lines


def insert_after_function(change, lines, filepath):
    """
    Insert content after a specified function in a file.

    Args:
        change: The change specification containing insert_after_function
        lines: List of file lines to modify
        filepath: Path to the file being modified

    Returns:
        None - modifies lines in place

    Raises:
        Exception: If the language is not supported or function can't be found
    """
    function_name = change["insert_after_function"]
    logger.info(f"insert_after_function {function_name}")

    # Get language handler for this file
    from jrdev.languages import get_language_for_file

    lang_handler = get_language_for_file(filepath)
    if not lang_handler:
        language = detect_language(filepath)
        raise Exception(f"Could not find language handler for file {filepath} (detected: {language})")

    # Get the language name for special handling
    language = lang_handler.language_name

    # Parse the function signature and file
    requested_class, requested_function = lang_handler.parse_signature(function_name)
    if requested_function is None:
        raise Exception(f"Could not parse requested {language} class: {function_name}\n")
    logger.info(f"requested class: {requested_class}")

    file_functions = lang_handler.parse_functions(filepath)

    # Find matching function
    matched_function = None
    potential_match = None
    for func in file_functions:
        if func["name"] == requested_function:
            # Check class match
            if requested_class is None:
                if func["class"] is None:
                    matched_function = func
                    break
                # mark as potential match, assign as match if nothing else found
                potential_match = func
                continue
            elif func["class"] is None:
                # No match, req has a class, this doesn't
                continue
            elif func["class"] == requested_class:
                matched_function = func
                break

    if matched_function is None and potential_match is not None:
        matched_function = potential_match

    if matched_function is None:
        message = f"Warning: Could not find function: '{requested_function}' class: {requested_class} in {filepath}\n  Available Functions: {file_functions}"
        terminal_print(message, PrintType.WARNING)
        logger.warning(message)
        raise Exception(message)

    # Get the end line index of the function (convert from 1-indexed to 0-indexed)
    func_end_idx = matched_function["end_line"] - 1

    # Prepare the new content and replace escaped newlines
    new_content = change["new_content"].replace("\\n", "\n").replace("\\\"", "\"")

    # Handle special case where new_content is intended to be just blank lines
    if new_content.strip() == "":
        newline_count = new_content.count('\n')
        logger.info(f"Inserting {newline_count} newlines")

        # Count existing blank lines after the function
        existing_blank_lines = 0
        i = func_end_idx + 1
        while i < len(lines) and lines[i].strip() == "":
            existing_blank_lines += 1
            i += 1

        logger.info(f"Found {existing_blank_lines} existing blank lines")

        # We just want to add the number of blank lines specified in the JSON,
        # not calculate a difference from existing blank lines
        lines_to_add = newline_count

        # For languages where indentation matters, handle it properly
        if language in ['typescript', 'go']:  # typescript includes JavaScript
            # Get the indentation level of the line after the function
            indentation = ""
            next_line_idx = func_end_idx + 1
            if next_line_idx < len(lines) and next_line_idx > 0:
                # Get indentation from the previous line
                prev_line = lines[func_end_idx]
                indentation_match = re.match(r'^(\s*)', prev_line)
                if indentation_match:
                    indentation = indentation_match.group(1)

            # Add the blank lines specified in new_content
            logger.info(f"Adding {lines_to_add} blank lines after function end (index {func_end_idx})")
            # We want to add blank lines right after the function, not after existing blank lines
            for _ in range(lines_to_add):
                lines.insert(func_end_idx + 1, indentation + "\n")
        else:
            # Add the blank lines specified in new_content for other languages
            logger.info(f"Adding {lines_to_add} blank lines after function end (index {func_end_idx})")
            for _ in range(lines_to_add):
                lines.insert(func_end_idx + 1, "\n")

        message = f"Inserting {newline_count} blank line(s) after function '{function_name}' in {filepath}"
        terminal_print(message, PrintType.INFO)
        logger.info(message)
        return

    # For non-blank content


    # Check if there's already a blank line after the function
    has_blank_line_after = (func_end_idx + 1 < len(lines) and lines[func_end_idx + 1].strip() == "")

    # Create the new content with proper line endings
    if has_blank_line_after:
        # There's already a blank line after the function, no need to add another
        new_content_lines = new_content.splitlines(True)  # Keep the line endings
    else:
        # Need to add a blank line separator
        new_content_lines = ["\n"] + new_content.splitlines(True)

    # Ensure the content ends with a newline
    if new_content_lines and not new_content_lines[-1].endswith('\n'):
        new_content_lines[-1] = new_content_lines[-1] + '\n'
    elif not new_content_lines:  # In case new_content was empty
        new_content_lines = ['\n']

    # Insert at the right position
    indentation_hint = change.get("indentation_hint")
    indent = indent_from_hint(indentation_hint, lines[func_end_idx])
    orig_first_line = new_content_lines[0]
    indent_all = True
    if indent != "":
        new_content_lines[0] = f"{indent}{new_content_lines[0].lstrip()}"
        if orig_first_line == new_content_lines[0] and orig_first_line[0] == " ":
            # no change was made, it came with white space, the other lines probably have correct indentation too
            indent_all = True
    else:
        new_content_lines[0] = f"{indent}{new_content_lines[0]}"

    # add indent in front of all lines
    if indent_all:
        i = 1
        while i < len(new_content_lines):
            new_content_lines[i] = f"{indent}{new_content_lines[i]}"
            i += 1


    lines[func_end_idx + 1:func_end_idx + 1] = new_content_lines

    message = f"Inserting content after function '{function_name}' in {filepath} with indent |{indent}|"
    terminal_print(message, PrintType.INFO)
    logger.info(message)

def insert_after_line(change, lines, filepath):
    """
    Insert content after a line containing specific text.

    Args:
        change: The change specification containing insert_after_line
        lines: List of file lines to modify
        filepath: Path to the file being modified

    Returns:
        None - modifies lines in place
    """
    insert_after_text = change["insert_after_line"]
    logger.info(f"insert_after_line '{insert_after_text}'")

    # Get the new content and replace escaped newlines
    new_content = change["new_content"].replace("\\n", "\n").replace("\\\"", "\"")

    # Find the line to insert after
    found = False
    for i, line in enumerate(lines):
        if insert_after_text.strip() in line.strip():
            # Prepare the new content
            new_lines = [
                line + ("\n" if not line.endswith("\n") else "")
                for line in new_content.split("\n")
            ]
            # Insert after the matching line
            lines = lines[:i + 1] + new_lines + lines[i + 1:]

            message = f"Inserting content after line containing '{insert_after_text}' in {filepath}"
            terminal_print(message, PrintType.INFO)
            logger.info(message)

            found = True
            break

    if not found:
        message = f"Warning: Could not find line '{insert_after_text}' in {filepath}"
        terminal_print(message, PrintType.WARNING)
        logger.warning(message)


def insert_within_function(change, lines, filepath):
    """
    Insert content within a function at a specific position.

    Args:
        change: The change specification containing insert_location.within_function
        lines: List of file lines to modify
        filepath: Path to the file being modified

    Returns:
        None - modifies lines in place
    """
    location = change["insert_location"]
    if "within_function" not in location:
        raise Exception(f"within_function not in insert_location: {change}")
    function_name = location["within_function"]

    if "position_marker" not in location:
        raise Exception(f"position_marker not in insert_location: {change}")
    position_marker = location["position_marker"]

    logger.info(f"insert_within_function '{function_name}' at position '{position_marker}'")

    lang_handler = get_language_for_file(filepath)
    if not lang_handler:
        language = detect_language(filepath)
        raise Exception(f"Could not find language handler for file {filepath} (detected: {language})")

    # Parse the function signature and file
    requested_class, requested_function = lang_handler.parse_signature(function_name)
    file_functions = lang_handler.parse_functions(filepath)

    # Find matching function
    matched_function = None
    potential_match = None
    for func in file_functions:
        if func["name"] == requested_function:
            # Check class match
            if requested_class is None:
                if func["class"] is None:
                    matched_function = func
                    break
                # mark as potential match, assign as match if nothing else found
                potential_match = func
                continue
            elif func["class"] is None:
                # No match, req has a class, this doesn't
                continue
            elif func["class"] == requested_class:
                matched_function = func
                break

    if matched_function is None and potential_match is not None:
        matched_function = potential_match

    if matched_function is None:
        message = f"Warning: Could not find function: '{requested_function}' class: {requested_class} in {filepath}\n  Available Functions: {file_functions}"
        terminal_print(message, PrintType.WARNING)
        logger.warning(message)
        return

    # Get the start and end line indexes (convert from 1-indexed to 0-indexed)
    func_start_idx = matched_function["start_line"] - 1
    func_end_idx = matched_function["end_line"] - 1

    # Prepare the new content and replace escaped newlines
    new_content = change["new_content"].replace("\\n", "\n").replace("\\\"", "\"")

    # Determine insert position based on position_marker
    insert_idx = None

    # position_marker may be a dict
    if isinstance(position_marker, dict):
        if "after_line" not in position_marker:
            raise Exception \
                (f"insert_within_function: position_marker is a dict, but after_line is not in it: {position_marker}")
        after_line = position_marker["after_line"]
        if isinstance(after_line, str):
            # This is not a line number but a string to match within the function
            line_matched = False
            # Search for the line containing the specified text within the function
            for i in range(func_start_idx, func_end_idx + 1):
                if after_line.strip() in lines[i].strip():
                    insert_idx = i + 1  # Insert after the matched line
                    line_matched = True
                    logger.info(f"insert_within_function matched line '{after_line}' at index {i}")
                    break

            if not line_matched:
                raise Exception \
                    (f"insert_within_function: Could not find line containing '{after_line}' in function '{function_name}' in '{filepath}'")
        else:
            # after_line is a number (relative line within the function)
            if not isinstance(after_line, (int, float)):
                after_line = int(after_line)  # Try to convert to integer

            # Validate that the line number is within function bounds
            if after_line < 0 or after_line > (func_end_idx - func_start_idx):
                raise Exception \
                    (f"insert_within_function: Line number {after_line} is out of bounds for function '{function_name}' (length: {func_end_idx - func_start_idx + 1} lines)")

            # Calculate the actual file line index
            insert_idx = func_start_idx + after_line + 1

        logger.info(f"insert_within_function after function line {after_line} file line {insert_idx}")
    elif position_marker == "at_start":
        # Insert after the opening brace of the function
        for i in range(func_start_idx, func_end_idx + 1):
            if "{" in lines[i]:
                insert_idx = i + 1
                break
        if insert_idx is None:
            insert_idx = func_start_idx + 1  # Default fallback
    elif position_marker == "before_return":
        # Find the last return statement in the function
        for i in range(func_end_idx, func_start_idx - 1, -1):
            if re.search(r'\breturn\b', lines[i]):
                insert_idx = i
                break
        if insert_idx is None:
            # location combination does not make sense, raise here
            raise Exception(f"insert_location: before_return within_function {requested_function} is not found")
    else:
        # Default to right after function declaration
        # todo, this should be first line after function scope
        insert_idx = func_start_idx + 1
        logger.info(f"insert_within_function defaulting to after func start")

    # Get indentation from the target line
    indentation_hint = change.get("indentation_hint")
    prev_line = lines[insert_idx - 1]
    indentation = indent_from_hint(indentation_hint, prev_line)

    # Prepare the content with proper indentation
    new_content_lines = []
    for line in new_content.splitlines(True):  # Keep line endings
        if line.strip():  # Only indent non-empty lines
            new_content_lines.append(indentation + line)
        else:
            new_content_lines.append(line)

    # Ensure the content ends with a newline
    if new_content_lines and not new_content_lines[-1].endswith('\n'):
        new_content_lines[-1] = new_content_lines[-1] + '\n'
    elif not new_content_lines:  # In case new_content was empty
        new_content_lines = ['\n']

    # Insert the content
    lines[insert_idx:insert_idx] = new_content_lines

    message = f"Inserting content within function '{function_name}' at {position_marker} in {filepath}"
    terminal_print(message, PrintType.INFO)
    logger.info(message)


def insert_after_marker(change, lines, filepath):
    """
    Insert content after a specific marker in the file.

    Args:
        change: The change specification containing insert_location.after_marker
        lines: List of file lines to modify
        filepath: Path to the file being modified

    Returns:
        None - modifies lines in place
    """
    marker = change["insert_location"]["after_marker"]
    logger.info(f"insert_after_marker '{marker}'")

    # Get the new content and replace escaped newlines
    new_content = change["new_content"].replace("\\n", "\n").replace("\\\"", "\"")

    # check indentation hint
    indentation_hint = None
    if "indentation_hint" in change:
        indentation_hint = change["indentation_hint"]

    # Find the line to insert after
    found = False
    for i, line in enumerate(lines):
        if marker.strip() in line.strip():
            # get suggested indent
            use_indentation = indent_from_hint(indentation_hint, line)

            # Prepare the new content with proper indentation
            new_content_lines = []
            for content_line in new_content.splitlines(True):  # Keep line endings
                if content_line.strip():  # Only indent non-empty lines
                    new_content_lines.append(use_indentation + content_line)
                else:
                    new_content_lines.append(content_line)

            # Ensure the content ends with a newline
            if new_content_lines and not new_content_lines[-1].endswith('\n'):
                new_content_lines[-1] = new_content_lines[-1] + '\n'
            elif not new_content_lines:  # In case new_content was empty
                new_content_lines = ['\n']

            # Insert after the matching line
            lines[i + 1:i + 1] = new_content_lines

            message = f"Inserting content after marker '{marker}' in {filepath}"
            terminal_print(message, PrintType.INFO)
            logger.info(message)

            found = True
            break

    if not found:
        message = f"Warning: Could not find marker '{marker}' in {filepath}"
        terminal_print(message, PrintType.WARNING)
        logger.warning(message)


def insert_global(change, lines, filepath):
    """
    Insert content at the global scope in the file.

    Args:
        change: The change specification containing insert_location.global
        lines: List of file lines to modify
        filepath: Path to the file being modified

    Returns:
        None - modifies lines in place
    """
    location = change["insert_location"]
    global_position = location.get("global", "end")  # Default to end if only { "global": true } is specified
    logger.info(f"insert_global at '{global_position}'")

    # Get the new content and replace escaped newlines
    new_content = change["new_content"].replace("\\n", "\n").replace("\\\"", "\"")

    # Determine where to insert the content
    if global_position == "start" or global_position is True:
        # Find the first non-import, non-comment line
        insert_idx = 0
        language = detect_language(filepath)

        # Skip shebang, imports, and comments based on language
        for i, line in enumerate(lines):
            # Skip shebang line
            if i == 0 and line.startswith("#!"):
                continue

            # Skip module docstring for Python
            if language == 'python' and i < 5 and line.strip().startswith('"""') or line.strip().startswith("'''"):
                # Skip until closing triple quote is found
                for j in range(i + 1, min(i + 20, len(lines))):
                    if '"""' in lines[j] or "'''" in lines[j]:
                        i = j + 1
                        break
                continue

            # Skip imports based on language
            if (language == 'python' and (line.strip().startswith('import ') or line.strip().startswith('from '))) or \
                    (language == 'typescript' and (
                            line.strip().startswith('import ') or line.strip().startswith('require('))) or \
                    (language == 'cpp' and (
                            line.strip().startswith('#include') or line.strip().startswith('using '))) or \
                    (language == 'go' and (line.strip().startswith('import ') or line.strip().startswith('package '))):
                continue

            # Skip comments
            if line.strip().startswith('//') or line.strip().startswith('#') or line.strip().startswith('/*'):
                continue

            # Found first non-import, non-comment line
            insert_idx = i
            break

        # Prepare new content lines
        new_content_lines = new_content.splitlines(True)  # Keep line endings

        # Ensure there's a blank line after the new content
        if insert_idx < len(lines) and new_content_lines and not new_content.endswith('\n\n'):
            new_content_lines.append('\n')

        # Insert at the beginning of the file (after imports)
        lines[insert_idx:insert_idx] = new_content_lines

        message = f"Inserting content at global scope (start) in {filepath}"
        terminal_print(message, PrintType.INFO)
        logger.info(message)

    else:  # "end" or any other value
        # Add to the end of the file
        # Check if file ends with newline
        if lines and not lines[-1].endswith('\n'):
            lines.append('\n')

        # Add a separator line if the file is not empty
        if lines and lines[-1].strip():
            lines.append('\n')

        # Add the new content
        new_content_lines = new_content.splitlines(True)  # Keep line endings
        lines.extend(new_content_lines)

        # Ensure file ends with a newline
        if lines and not lines[-1].endswith('\n'):
            lines.append('\n')

        message = f"Inserting content at global scope (end) in {filepath}"
        terminal_print(message, PrintType.INFO)
        logger.info(message)


def indent_from_hint(hint, prev_line):
    prev_line_indent = prev_line[:len(prev_line) - len(prev_line.lstrip())]
    indent_level = " " * 4
    use_indentation = ""
    if hint == "maintain_indent":
        use_indentation = prev_line_indent
    elif hint == "increase_indent":
        use_indentation = prev_line_indent + indent_level
    elif hint == "decrease_indent":
        # Remove one indent level if possible; otherwise, use no indentation.
        if len(prev_line_indent) >= len(indent_level):
            use_indentation = prev_line_indent[:-len(indent_level)]
        else:
            use_indentation = ""
    else:
        # default
        indentation_match = re.match(r'^(\s*)', prev_line)
        if indentation_match:
            use_indentation = indentation_match.group(1)
    return use_indentation