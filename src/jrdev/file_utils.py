import re
import os
import glob
import difflib
from difflib import SequenceMatcher
import numbers
import fnmatch
import pprint

from jrdev.ui import terminal_print, PrintType


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
        formatted_content += f"\n\n--- {path} ---\n{content}"
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
    result = ""

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
                if num_start > -1:
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
                            raise Exception(f"UNHANDLED NUMBER**** {num_str}")
                        continue

                    continue

                num_start = i
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


def check_and_apply_code_changes(response_text):
    cutoff = cutoff_string(response_text, "```json", "```")
    new_files = manual_json_parse(cutoff)

    if "files" in new_files:
        for file in new_files["files"]:
            if file['filename'] in file['path']:
                write_string_to_file(file['filename'], file["content"])
            else:
                full_path = f"{file['path']}{file['filename']}"
                write_string_to_file(full_path, file["content"])