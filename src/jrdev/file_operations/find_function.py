import logging

from jrdev.languages import get_language_for_file
from jrdev.languages.utils import detect_language
from jrdev.ui.ui import PrintType

# Get the global logger instance
logger = logging.getLogger("jrdev")


def find_function(function_name, filepath):

    lang_handler = get_language_for_file(filepath)
    if not lang_handler:
        language = detect_language(filepath)
        logger.info(f"Could not find language handler for file {filepath} (detected: {language})")
        return None

    # Get the language name for special handling
    language = lang_handler.language_name

    # Parse the function signature and file
    requested_class, requested_function = lang_handler.parse_signature(function_name)
    if requested_function is None:
        logger.info(f"Could not parse requested {language} class: {function_name}\n")
        return None

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
        logger.warning(message)
        return None

    return matched_function
