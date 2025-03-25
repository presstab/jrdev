import glob
import logging
import os
import re
from difflib import SequenceMatcher

from jrdev.languages.utils import detect_language, is_headers_language
from jrdev.ui.ui import terminal_print, PrintType

JRDEV_DIR = "jrdev/"


# Get the global logger instance
logger = logging.getLogger("jrdev")


def requested_files(text):
    match = re.search(r"get_files\s+(\[.*?\])", text, re.DOTALL)
    file_list = []
    if match:
        file_list_str = match.group(1)
        file_list_str = file_list_str.replace("'", '"')
        try:
            file_list = eval(file_list_str)
        except Exception as e:
            terminal_print(f"Error parsing file list: {str(e)}", PrintType.ERROR)
            file_list = []

    if file_list == []:
        return file_list

    # Check if language has headers for classes, if so make sure both header and source file are included in files_to_send
    checked_files = set(file_list)
    additional_files = []

    for file in file_list:
        language = detect_language(file)
        if is_headers_language(language):
            base_name, ext = os.path.splitext(file)

            # If it's a header file (.h, .hpp), look for corresponding source file (.cpp, .cc)
            if ext.lower() in ['.h', '.hpp']:
                for source_ext in ['.cpp', '.cc', '.cxx', '.c++']:
                    source_file = f"{base_name}{source_ext}"
                    if os.path.exists(source_file) and source_file not in checked_files:
                        logger.info(f"Adding corresponding source file: {source_file}")
                        additional_files.append(source_file)
                        checked_files.add(source_file)
                        break

            # If it's a source file (.cpp, .cc), look for corresponding header file (.h, .hpp)
            elif ext.lower() in ['.cpp', '.cc', '.cxx', '.c++']:
                for header_ext in ['.h', '.hpp']:
                    header_file = f"{base_name}{header_ext}"
                    if os.path.exists(header_file) and header_file not in checked_files:
                        logger.info(f"Adding corresponding header file: {header_file}")
                        additional_files.append(header_file)
                        checked_files.add(header_file)
                        break

    # Add the additional files to the list
    file_list.extend(additional_files)
    return file_list


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
                    terminal_print(f"Error reading file {file_path}: File not found", PrintType.ERROR)
        except Exception as e:
            terminal_print(f"Error reading file {file_path}: {str(e)}", PrintType.ERROR)

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


def add_to_gitignore(gitignore_path: str, ignore_str: str, create_if_dne: bool = False) -> bool:
    """
    Append a pattern to a .gitignore file. Creates the file if it doesn't exist.

    Args:
        gitignore_path: The path to the .gitignore file
        ignore_str: The pattern to add to the .gitignore file

    Returns:
        True if the pattern was added successfully, False otherwise
    """
    try:
        # Make sure the pattern is properly formatted
        ignore_pattern = ignore_str.strip()

        # Check if the file exists
        if os.path.exists(gitignore_path):
            # Read existing contents to check if the pattern already exists
            with open(gitignore_path, 'r') as f:
                lines = f.read().splitlines()

            # Check if pattern already exists
            if ignore_pattern in lines:
                return True

            # Add a newline at the end if needed
            needs_newline = lines and lines[-1] != ""

            # Append the pattern to the file
            with open(gitignore_path, 'a') as f:
                if needs_newline:
                    f.write("\n")
                f.write(f"{ignore_pattern}\n")

            terminal_print(f"Added '{ignore_pattern}' to {gitignore_path}", PrintType.SUCCESS)
        elif create_if_dne:
            # File doesn't exist, create it with the pattern
            with open(gitignore_path, 'w') as f:
                f.write(f"{ignore_pattern}\n")

            terminal_print(f"Created {gitignore_path} with pattern '{ignore_pattern}'", PrintType.SUCCESS)

        return True

    except Exception as e:
        terminal_print(f"Error adding to gitignore: {str(e)}", PrintType.ERROR)
        logger.error(f"Error adding to gitignore: {str(e)}")
        return False


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
        # We'll handle boolean values in the character loop instead
        # to avoid processing them when they're inside quotes

        i = -1
        for char in line:
            i += 1

            if char == ":" and skip_colon:
                skip_colon = False
                continue

            # Handle boolean literals - but only outside of quotes
            if pending_key and not quote_open and i + 4 <= len(line) and line[i:i+4] == "true":
                stack[-1][pending_key] = True
                pending_key = ""
                i += 3  # Skip the rest of 'true'
                continue
            if pending_key and not quote_open and i + 5 <= len(line) and line[i:i+5] == "false":
                stack[-1][pending_key] = False
                pending_key = ""
                i += 4  # Skip the rest of 'false'
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
                                logger.info(f"UNHANDLED QUOTE END 268 char: {char} line:{line}")
                                raise Exception("malformed JSON")
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
                            logger.info(f"UNHANDLED QUOTE END 230 char: {char} line:{line}")
                            raise Exception("malformed JSON")
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
                    logger.info(f"UNHANDLED NUMBER* 264*** {num_str}")
                    raise Exception("malformed JSON")
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
