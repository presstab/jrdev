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
from jrdev.cpp import parse_cpp_signature, parse_cpp_functions
from jrdev.py_lang import parse_python_signature, parse_python_functions
from jrdev.ts_lang import parse_typescript_signature, parse_typescript_functions

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
        str: Language identifier ('cpp', 'python', etc.)
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
        '.js': 'javascript',
        '.ts': 'typescript',
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
    
    # Detect the language
    language = detect_language(filepath)
    if not language:
        raise Exception(f"Could not detect language for file: {filepath}")

    requested_class = None
    requested_function = None
    file_functions = None

    # Handle based on language
    if language == 'cpp':
        # Parse the function signature to get class and function name
        requested_class, requested_function = parse_cpp_signature(function_name)
        file_functions = parse_cpp_functions(filepath)
    elif language == 'python':
        # Parse the Python function signature
        requested_class, requested_function = parse_python_signature(function_name)
        file_functions = parse_python_functions(filepath)
    elif language in ['typescript', 'javascript']:
        # Parse the TypeScript/JavaScript function signature
        requested_class, requested_function = parse_typescript_signature(function_name)
        file_functions = parse_typescript_functions(filepath)
    else:
        # Other languages not supported yet
        raise Exception(f"Language {language} is not supported for insert_after_function yet")
    
    # Find matching function
    matched_function = None
    for func in file_functions:
        if func["name"] == requested_function:
            # Check class match
            if requested_class is None:
                if func["class"] is None:
                    matched_function = func
                    break
            elif func["class"] is None:
                # No match, req has a class, this doesn't
                continue
            elif func["class"] == requested_class:
                matched_function = func
                break

    if matched_function is None:
        message = f"Warning: Could not find function: '{requested_function}' class: {requested_class} in {filepath}"
        terminal_print(message, PrintType.WARNING)
        logger.warning(message)
        return

    # Get the end line index of the function (convert from 1-indexed to 0-indexed)
    func_end_idx = matched_function["end_line"] - 1
    
    # Prepare the new content
    new_content = change["new_content"]
    
    # Handle special case where new_content is intended to be just blank lines
    if new_content.strip() == "":
        newline_count = new_content.count('\n')
        
        # Count existing blank lines after the function
        existing_blank_lines = 0
        i = func_end_idx + 1
        while i < len(lines) and lines[i].strip() == "":
            existing_blank_lines += 1
            i += 1
        
        # Calculate how many more blank lines we need to add
        lines_to_add = newline_count - existing_blank_lines
        
        # For TypeScript, we need to handle indentation properly
        if language in ['typescript', 'javascript']:
            # Get the indentation level of the line after the function
            indentation = ""
            next_line_idx = func_end_idx + 1
            if next_line_idx < len(lines) and next_line_idx > 0:
                # Get indentation from the previous line
                prev_line = lines[func_end_idx]
                indentation_match = re.match(r'^(\s*)', prev_line)
                if indentation_match:
                    indentation = indentation_match.group(1)
                
            # Add the needed blank lines with proper indentation
            for _ in range(max(0, lines_to_add)):
                lines.insert(func_end_idx + 1, indentation + "\n")
        else:
            # Add the needed blank lines without special indentation
            for _ in range(max(0, lines_to_add)):
                lines.insert(func_end_idx + 1 + existing_blank_lines, "\n")
                
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
    
    # Get the new content
    new_content = change["new_content"]

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

def process_insert_after_changes(lines, insert_after_changes, filepath):
    """
    Process changes based on insert_type directive (insert_after_line or insert_after_function).
    
    Args:
        lines: List of file lines
        insert_after_changes: List of changes with insert_after_line or insert_after_function
        filepath: Path to the file being modified
        
    Returns:
        Updated list of lines
    """
    for change in insert_after_changes:
        if "filename" not in change:
            raise Exception(f"filename not in change: {change}")
        if "new_content" not in change:
            raise Exception(f"new_content not in change: {change}")
        if "insert_type" not in change:
            raise Exception(f"insert_type not in change: {change}")
        
        # Use helper functions to check for insert types
        insert_type = change["insert_type"]
        has_after_line = "insert_after_line" in insert_type
        has_after_function = "insert_after_function" in insert_type
        
        # Handle invalid insert_type
        if not (has_after_line or has_after_function):
            raise Exception(f"Invalid insert_type '{change['insert_type']}' or missing required parameters in change: {change}")
        
        change["new_content"] = change["new_content"].replace("\\n", "\n").replace("\\\"", "\"")
        
        # Check if this is a FUNCTION sub_type that needs special handling at the end of file
        # if "sub_type" in change and change["sub_type"] == "FUNCTION" and not has_insert_after_function and not has_insert_after_line:
        #     lines, start_idx, end_idx, new_lines = process_function_subtype(lines, new_content, filepath)
        #     lines = lines[:start_idx] + new_lines + lines[end_idx:]
        #     continue
        
        # Process insert_after_function if it exists
        if has_after_function:
            insert_after_function(change, lines, filepath)
            continue  # Skip to the next change after processing insert_after_function
        
        # Process insert_after_line if it exists
        if has_after_line:
            insert_after_line(change, lines, filepath)
            continue
            
    return lines


def apply_file_changes(changes_json):
    """
    Apply changes to files based on the provided JSON.
    
    The function supports multiple ways to specify changes:
    1. Using operation=ADD/DELETE with start_line
    2. Using insert_type with options:
       - insert_after_line: to specify a line of code after which to insert
       - insert_after_function: to specify a function after which to insert new code
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
        insert_after_changes = [c for c in changes if "insert_after_line" in c or "insert_after_function" in c]
        
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
