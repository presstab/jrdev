import logging
import os
import tempfile
from difflib import unified_diff
import shutil

from jrdev.ui.ui import terminal_print, PrintType, display_diff, prompt_for_confirmation
from jrdev.ui.diff_editor import curses_editor
from jrdev.file_operations.add import process_add_operation
from jrdev.file_operations.delete import process_delete_operation
from jrdev.file_operations.replace import process_replace_operation
from jrdev.file_operations.insert import process_insert_after_changes
from jrdev.file_utils import find_similar_file

# Get the global logger instance
logger = logging.getLogger("jrdev")


def write_with_confirmation(filepath, content):
    """
    Writes content to a temporary file, shows diff, and asks for user confirmation
    before writing to the actual file.

    Args:
        filepath (str): Path to the file to write to
        content (list or str): Content to write to the file

    Returns:
        Tuple of (result, message):
            - result: True if write was confirmed and successful, False otherwise
            - message: User feedback if they requested changes, None otherwise
    """
    # Convert content to string if it's a list of lines
    if isinstance(content, list):
        content_str = ''.join(content)
    else:
        content_str = content

    # Create a temporary file
    with tempfile.NamedTemporaryFile(
            delete=False, mode='w', encoding='utf-8') as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(content_str)

    try:
        # Read original file content if it exists
        original_content = ""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()

        # Generate diff
        original_lines = original_content.splitlines(True)
        new_lines = content_str.splitlines(True)

        diff = list(unified_diff(
            original_lines,
            new_lines,
            fromfile=f'a/{filepath}',
            tofile=f'b/{filepath}',
            n=3
        ))

        # Display diff using the UI function
        display_diff(diff)
        
        while True:
            # Ask for confirmation using the UI function
            response, message = prompt_for_confirmation("Apply these changes?")
            
            if response == 'yes':
                # Copy temp file to destination
                directory = os.path.dirname(filepath)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                shutil.copy2(temp_file_path, filepath)
                terminal_print(f"Changes applied to {filepath}", PrintType.SUCCESS)
                return True, None
            elif response == 'no':
                terminal_print(f"Changes to {filepath} discarded", PrintType.WARNING)
                return False, None
            elif response == 'request_change':
                terminal_print(f"Changes to {filepath} not applied, feedback requested", PrintType.WARNING)
                return False, message
            elif response == 'edit':
                
                # Convert diff to a list of lines for the editor
                edited_diff = curses_editor(diff)
                
                if edited_diff:
                    # The user saved changes in the editor
                    
                    # Write the edited content to a new temp file
                    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as new_temp_file:
                        new_temp_path = new_temp_file.name
                        new_temp_file.write('\n'.join(edited_diff))
                    
                    # Show the new diff
                    terminal_print("Updated changes:", PrintType.HEADER)
                    display_diff(edited_diff)
                    
                    # Update the temp file path to the new one
                    os.unlink(temp_file_path)
                    temp_file_path = new_temp_path
                    
                    # Continue the loop to prompt again with the updated diff
                    terminal_print("Edited changes prepared. Please confirm:", PrintType.INFO)
                else:
                    # User quit without saving or an error occurred
                    terminal_print("Edit cancelled or no changes made.", PrintType.WARNING)
                    # Continue the confirmation loop
                    continue

    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

    return False, None


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
    4. Using operation=REPLACE to replace content in a file
    """
    # Group changes by filename
    changes_by_file = {}
    new_files = []
    files_changed = []

    valid_operations = ["ADD", "DELETE", "REPLACE", "NEW", "RENAME", "NEW"]

    for change in changes_json["changes"]:
        if "operation" not in change:
            terminal_print(f"apply_file_changes: malformed change request: {change}")
            continue

        operation = change["operation"]
        if operation not in valid_operations:
            terminal_print(
                f"apply_file_changes: malformed change request, bad operation: {operation}")
            if operation == "MODIFY":
                operation = "REPLACE"
                terminal_print("switching MODIFY to REPLACE")
            else:
                continue

        # Handle NEW operation separately
        if operation == "NEW":
            new_files.append(change)
            continue

        filename = change["filename"]
        changes_by_file.setdefault(filename, []).append(change)

    for filename, changes in changes_by_file.items():
        # Read the file into a list of lines
        filepath = filename
        if not os.path.exists(filename):
            try:
                filepath = find_similar_file(filename)
            except Exception:
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
        replace_changes = [
            c for c in changes if "operation" in c and c["operation"] == "REPLACE"]

        # Process operation-based changes first
        if operation_changes:
            lines = process_operation_changes(lines, operation_changes, filename)

        # Process insert_after_line based changes
        lines = process_insert_after_changes(lines, insert_after_changes, filepath)

        # Process replace changes
        for change in replace_changes:
            lines = process_replace_operation(lines, change, filepath)

        # Write the updated lines to a temp file, show diff, and ask for confirmation
        result, user_message = write_with_confirmation(filepath, lines)
        if result:
            files_changed.append(filepath)
            message = f"Updated {filepath}"
            logger.info(message)
        else:
            if user_message:
                message = f"Update to {filepath} was not applied. User requested changes: {user_message}"
                return {"success": False, "change_requested": user_message}
            else:
                message = f"Update to {filepath} was cancelled by user"
                return {"success": False}

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

        # Write the new file with confirmation
        result, user_message = write_with_confirmation(filepath, new_content)
        if result:
            files_changed.append(filepath)
            message = f"Created new file: {filepath}"
            logger.info(message)
        else:
            if user_message:
                message = f"Creation of {filepath} was not applied. User requested changes: {user_message}"
                return {"success": False, "change_requested": user_message}
            else:
                message = f"Creation of {filepath} was cancelled by user"
            logger.info(message)

    return {"success": True, "files_changed": files_changed}


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