import re
import os
import glob
import difflib
from difflib import SequenceMatcher
import numbers
import fnmatch
import pprint
import logging

from jrdev.ui import terminal_print, PrintType
from jrdev.languages import get_language_for_file
from jrdev.languages.utils import detect_language_for_file

# Get the global logger instance
logger = logging.getLogger("jrdev")


def requested_files(text):
    match = re.search(r"get_files\s+(\[.*?\])", text, re.DOTALL)
    if match:
        file_list_str = match.group(1)
        file_list_str = file_list_str.replace("'", '"')
        try:
            file_list = eval(file_list_str)
        except Exception as e:
            terminal_print(f"Error parsing file list: {str(e)}", PrintType.ERROR)
            file_list = []
        return file_list
    return []


def find_similar_file(file_path):
    """
    Attempts to find a similar file when the exact path doesn't match.
    """
    original_filename = os.path.basename(file_path)
    original_dirname = os.path.dirname(file_path)

    # Strategy 1: Look for exact filename in any directory
    try:
        matches = []
        for root, _, files in os.walk('.'):
            if original_filename in files:
                matches.append(os.path.join(root, original_filename))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            matches.sort(key=lambda m: SequenceMatcher(None, os.path.dirname(m), original_dirname).ratio(), reverse=True)
            return matches[0]
    except Exception:
        pass

    # Strategy 2: Fuzzy matching in the same directory
    try:
        if os.path.exists(original_dirname):
            files_in_dir = [f for f in os.listdir(original_dirname) if os.path.isfile(os.path.join(original_dirname, f))]
            if files_in_dir:
                similar_files = sorted(files_in_dir, key=lambda f: SequenceMatcher(None, f, original_filename).ratio(), reverse=True)
                best_match = similar_files[0]
                if SequenceMatcher(None, best_match, original_filename).ratio() > 0.6:
                    return os.path.join(original_dirname, best_match)
    except Exception:
        pass

    # Strategy 3: Glob matching for similar extensions
    try:
        ext = os.path.splitext(original_filename)[1]
        if ext:
            pattern = f"**/*{ext}"
            matches = glob.glob(pattern, recursive=True)
            if matches:
                matches.sort(key=lambda m: SequenceMatcher(None, os.path.basename(m), original_filename).ratio(), reverse=True)
                best_match = matches[0]
                if SequenceMatcher(None, os.path.basename(best_match), original_filename).ratio() > 0.5:
                    return best_match
    except Exception:
        pass

    return None


def get_file_contents(file_list):
    """
    Reads the contents of a list of files. If a file doesn't exist, it attempts to find a similar file.
    """
    file_contents = {}
    for file_path in file_list:
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, "r") as f:
                    file_contents[file_path] = f.read()
            else:
                similar_file = find_similar_file(file_path)
                if similar_file:
                    terminal_print(f"\nFound similar file: {similar_file} instead of {file_path}", PrintType.WARNING)
                    with open(similar_file, "r") as f:
                        file_contents[file_path] = f.read()
                else:
                    file_contents[file_path] = f"Error: File not found: {file_path}"
        except Exception as e:
            file_contents[file_path] = f"Error reading file {file_path}: {str(e)}"

    formatted_content = ""
    for path, content in file_contents.items():
        formatted_content += f"\n\n--- BEGIN FILE: {path} ---\n{content}\n--- END FILE: {path} ---\n"

    return formatted_content


def cutoff_string(input_string, cutoff_before_match, cutoff_after_match):
    """
    Cuts off parts of the input string before the first occurrence of cutoff_before_match
    and after the second occurrence of cutoff_after_match.

    Parameters:
    - input_string (str): The original string.
    - cutoff_before_match (str): The phrase before which all text will be cut off (including this).
    - cutoff_after_match (str): The phrase after which all text will be cut off (second occurance and including this).

    Returns:
    - str: The modified string.
    """
    try:
        # Find the index of the first occurrence of cutoff_before_match
        start_index = input_string.index(cutoff_before_match)
        cropped = input_string[start_index + len(cutoff_before_match):]

        match2 = cropped.index(cutoff_after_match)
        cropped = cropped[0:(match2 + - len(cutoff_after_match))]

        # Return the substring between the two indices
        return cropped.strip()

    except ValueError:
        # If either phrase is not found or the order is incorrect, return the original string
        return input_string


def write_string_to_file(filename: str, content: str):
    """
    Writes a given string to a file, correctly interpreting '\n' as line breaks.

    :param filename: The name of the file to write to.
    :param content: The string content to write, including line breaks.
    """
    content = content.replace("\\n", "\n").replace("\\\"", "\"")
    with open(filename, 'w', encoding='utf-8') as file:
        terminal_print(f"Writing {filename}", PrintType.WARNING)
        file.write(content)


def manual_json_parse(text):
    """
    Manually parses a JSON-like text by processing it line by line.
    This simple parser uses a stack to build nested dictionaries and lists.
    (It assumes that the input is well formatted and does not cover every JSON edge case.)
    """
    # Split the input text into non-empty lines.
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    nums = "0123456789"
    pending_key = ""
    main_object = {}
    stack = []
    stack.append(main_object)

    quote_text = ""
    quote_open = False
    skip_colon = True

    for line in lines:

        # if line has markdown, remove it
        if "```json" in line:
            if len(line) == len("```json"):
                continue
            #todo handle if valid json is on same line

        num_start = -1

        i = -1
        for char in line:
            i += 1

            if char == ":" and skip_colon:
                skip_colon = False
                continue

            if char == "\"":
                #check if it is escaped
                is_escaped = i > 0 and line[i - 1] == "\\"

                if quote_open:
                    if is_escaped:
                        quote_text += "\""
                        continue

                    #close quote now
                    quote_open = False

                    # this is either naming a new key or is a value, check next char
                    if i + 1 < len(line):
                        next_char = line[i+1]
                        if next_char == ":":
                            #just named a value
                            pending_key = quote_text
                            quote_text = ""

                            skip_colon = True
                        elif pending_key:
                            #simple kv pair, and quote text is the value?
                            stack[-1][pending_key] = quote_text
                            quote_text = ""
                            pending_key = ""
                        elif next_char == "," or next_char == "]":
                            # possible list of strings
                            if isinstance(stack[-1], list):
                                stack[-1].append(quote_text)
                                quote_text = ""
                                continue
                            else:
                                raise Exception("UNHANDLED QUOTE END")
                    else:
                        # last character of this line.. no comma end? probably last in a container?
                        if pending_key:
                            stack[-1][pending_key] = quote_text
                            quote_text = ""
                            pending_key = ""
                            continue
                        elif isinstance(stack[-1], list):
                            stack[-1].append(quote_text)
                            quote_text = ""
                            continue
                        else:
                            raise Exception("UNHANDLED QUOTE END 230")
                    continue
                else:
                    #start of new quote
                    quote_open = True
                    continue

            if quote_open:
                #quote is open, just add to quote text
                quote_text += char
                continue

            if char in nums:

                if num_start == -1:
                    num_start = i

                num_end = i

                #check if this is last digit
                if i + 1 < len(line):
                    if line[i+1] in nums:
                        continue

                #last instance, now compile as full number
                num_str = line[num_start:(num_end+1)]
                num_start = -1
                n = int(num_str)
                if pending_key:
                    stack[-1][pending_key] = n
                    pending_key = ""
                elif isinstance(stack[-1], list):
                    stack[-1].append(n)
                else:
                    raise Exception(f"UNHANDLED NUMBER* 264*** {num_str}")
                continue

            # object start
            if char == "{":
                # new object
                if not main_object:
                    # just start of main object
                    continue

                # is there a pending kv pair?
                if pending_key:
                    obj_new = {}
                    stack[-1][pending_key] = obj_new
                    stack.append(obj_new)
                    pending_key = ""
                    continue

                if isinstance(stack[-1], list):
                    # add new object to list
                    new_obj = {}
                    stack[-1].append(new_obj)
                    stack.append(new_obj)
                    continue

            if char == "[":
                #new array
                if pending_key:
                    new_list = []
                    stack[-1][pending_key] = new_list
                    stack.append(new_list)
                    pending_key = ""
                    continue
            if char == "]":
                # end of array
                assert isinstance(stack[-1], list)
                stack.pop()
                continue
            if char == "}":
                # end of object
                assert isinstance(stack[-1], dict)
                stack.pop()
                continue

    return main_object


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


def process_operation_changes(lines, operation_changes, filename):
    """
    Process changes based on operation (ADD/DELETE) and start_line.
    
    Args:
        lines: List of file lines
        operation_changes: List of changes with operation and start_line
        filename: Name of the file being modified
        
    Returns:
        Updated list of lines
    """
    # Sort changes in descending order of start_line
    operation_changes.sort(key=lambda c: c["start_line"], reverse=True)
    
    for change in operation_changes:
        operation = change["operation"]
        
        if "filename" not in change:
            raise Exception(f"filename not in change: {change}")

        if operation == "DELETE" and "end_line" not in change:
            raise Exception(f"end_line not in change: {change}")

        if operation == "ADD" and "new_content" not in change:
            raise Exception(f"new_content not in change: {change}")

        # Process the operation based on its type
        if operation == "ADD":
            lines = process_add_operation(lines, change, filename)
        elif operation == "DELETE":
            lines = process_delete_operation(lines, change)
            
    return lines

def detect_language(filepath):
    """
    Detect the programming language based on file extension.
    
    Args:
        filepath: Path to the file
        
    Returns:
        str: Language identifier ('cpp', 'python', 'typescript', etc.)
        
    Note:
        For implementation simplicity, JavaScript files are treated as 'typescript'
        since the same parser handles both languages.
    """
    ext = os.path.splitext(filepath)[1].lower()
    
    # Map file extensions to language identifiers
    lang_map = {
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.c++': 'cpp',
        '.hpp': 'cpp',
        '.h': 'cpp',
        '.py': 'python',
        '.js': 'typescript',  # Use TypeScript parser for JavaScript
        '.jsx': 'typescript', # React JSX also uses TypeScript parser
        '.ts': 'typescript',
        '.tsx': 'typescript', # TypeScript React
        '.go': 'go',
        '.java': 'java',
        '.rb': 'ruby',
        '.rs': 'rust',
        '.swift': 'swift',
        '.php': 'php',
        '.cs': 'csharp',
    }
    
    # Return the language or None if not recognized
    return lang_map.get(ext)


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
    print(f"requested class: {requested_class}")

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
    
    # Insert at the right position
    lines[func_end_idx + 1:func_end_idx + 1] = new_content_lines
    
    message = f"Inserting content after function '{function_name}' in {filepath}"
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
    function_name = location["within_function"]
    position_marker = location.get("position_marker", "at_start")
    
    logger.info(f"insert_within_function '{function_name}' at position '{position_marker}'")
    
    # Get language handler for this file
    from jrdev.languages import get_language_for_file
    
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
    
    if position_marker == "at_start":
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
            insert_idx = func_end_idx  # Default fallback
    
    else:
        # Default to right after function declaration
        insert_idx = func_start_idx + 1
    
    # Get indentation from the target line
    indentation = ""
    if insert_idx < len(lines):
        indentation_match = re.match(r'^(\s*)', lines[insert_idx])
        if indentation_match:
            indentation = indentation_match.group(1)
    
    # Prepare the content with proper indentation
    new_content_lines = []
    for line in new_content.splitlines(True):  # Keep line endings
        if line.strip():  # Only indent non-empty lines
            new_content_lines.append(indentation + line)
        else:
            new_content_lines.append(line)
    
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
    
    # Find the line to insert after
    found = False
    for i, line in enumerate(lines):
        if marker.strip() in line.strip():
            # Determine indentation
            indentation = ""
            indentation_match = re.match(r'^(\s*)', line)
            if indentation_match:
                indentation = indentation_match.group(1)
            
            # Prepare the new content with proper indentation
            new_content_lines = []
            for content_line in new_content.splitlines(True):  # Keep line endings
                if content_line.strip():  # Only indent non-empty lines
                    new_content_lines.append(indentation + content_line)
                else:
                    new_content_lines.append(content_line)
            
            # Insert after the matching line
            lines[i+1:i+1] = new_content_lines
            
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
               (language == 'typescript' and (line.strip().startswith('import ') or line.strip().startswith('require('))) or \
               (language == 'cpp' and (line.strip().startswith('#include') or line.strip().startswith('using '))) or \
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
                marker_change = change.copy()
                marker_change["insert_location"] = {"after_marker": location["after_line"]}
                insert_after_marker(marker_change, lines, filepath)
                terminal_print(f"Warning: 'after_line' is deprecated, use 'after_marker' instead", PrintType.WARNING)
                continue
                
            else:
                raise Exception(f"Invalid insert_location, missing a valid location type: {change}")
        else:
            raise Exception(f"Missing insert_location in change: {change}")
            
    return lines


def apply_file_changes(changes_json):
    """
    Apply changes to files based on the provided JSON.
    
    The function supports multiple ways to specify changes:
    1. Using operation=ADD/DELETE with start_line
    2. Using insert_location object with options:
       - after_line: to specify a line of code after which to insert
       - after_function: to specify a function after which to insert new code
       (more reliable for LLM-based edits)
    3. Using operation=NEW to create a new file
    """
    # Group changes by filename
    changes_by_file = {}
    new_files = []
    files_changed = []

    for change in changes_json["changes"]:
        # Handle NEW operation separately
        if "operation" in change and change["operation"] == "NEW":
            new_files.append(change)
            continue
            
        filename = change["filename"]
        changes_by_file.setdefault(filename, []).append(change)

    for filename, changes in changes_by_file.items():
        # Read the file into a list of lines
        filepath = filename
        if os.path.exists(filename) == False:
            try:
                filepath = find_similar_file(filename)
            except Exception as e:
                terminal_print(f"File not found: {filepath}", PrintType.ERROR)
                continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            terminal_print(f"File not found: {filepath}", PrintType.ERROR)
            continue
        except Exception as e:
            terminal_print(f"Error reading {filepath}: {str(e)}", PrintType.ERROR)
            continue

        # Process classic operation-based changes (start_line based)
        operation_changes = [c for c in changes if "operation" in c and "start_line" in c]
        insert_after_changes = [c for c in changes if "insert_location" in c]
        
        # Process operation-based changes first
        if operation_changes:
            lines = process_operation_changes(lines, operation_changes, filename)
        
        # Process insert_after_line based changes
        lines = process_insert_after_changes(lines, insert_after_changes, filepath)

        # Write the updated lines back to the file
        with open(filepath, "w", encoding="utf-8") as f:
            files_changed.append(filepath)
            f.writelines(lines)
            message = f"Updated {filepath}"
            terminal_print(message, PrintType.WARNING)
            logger.info(message)
    
    # Process new file creations
    for change in new_files:
        if "filename" not in change:
            raise Exception(f"filename not in change: {change}")
        if "new_content" not in change:
            raise Exception(f"new_content not in change: {change}")
        
        filepath = change["filename"]
        new_content = change["new_content"]
        new_content = new_content.replace("\\n", "\n").replace("\\\"", "\"")
        
        # Create directories if they don't exist
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            message = f"Created directory: {directory}"
            terminal_print(message, PrintType.INFO)
            logger.info(message)
        
        # Write the new file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
            files_changed.append(filepath)
            message = f"Created new file: {filepath}"
            terminal_print(message, PrintType.WARNING)
            logger.info(message)

    return files_changed


def check_and_apply_code_changes(response_text):
    cutoff = cutoff_string(response_text, "```json", "```")
    changes = manual_json_parse(cutoff)

    if "changes" in changes:
        return apply_file_changes(changes)
    return []
