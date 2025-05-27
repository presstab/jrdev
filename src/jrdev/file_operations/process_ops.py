import logging
import os
import re
import shutil
import tempfile
from difflib import unified_diff

from jrdev.file_operations.add import process_add_operation
from jrdev.file_operations.delete import process_delete_operation
from jrdev.file_operations.replace import process_replace_operation
from jrdev.file_operations.diff_markup import apply_diff_markup
from jrdev.file_utils import find_similar_file
from jrdev.ui.ui import PrintType, display_diff

# Get the global logger instance
logger = logging.getLogger("jrdev")

class CodeTaskCancelled(Exception):
    """
    Exception to signal that the code task was cancelled by the user.
    """
    pass

def apply_diff_to_content(original_content, diff_lines):
    """
    Apply edited diff lines to original content.

    Args:
        original_content (str): The original file content
        diff_lines (list): The edited diff lines

    Returns:
        str: The new content with diff applied
    """
    # We need to parse the diff and apply the changes
    original_lines = original_content.splitlines()
    result_lines = original_lines.copy()

    # Parse the unified diff
    current_line = 0
    hunk_start = None
    hunk_offset = 0

    # Skip the header lines (path info)
    while current_line < len(diff_lines) and not diff_lines[current_line].startswith('@@'):
        current_line += 1

    while current_line < len(diff_lines):
        line = diff_lines[current_line]

        # New hunk
        if line.startswith('@@'):
            # Parse the @@ -a,b +c,d @@ line to get line numbers
            match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line)
            if match:
                old_start, old_count, new_start, new_count = map(int, match.groups())
                hunk_start = old_start - 1  # 0-based indexing
                hunk_offset = 0
            current_line += 1
            continue

        # Deleted line (starts with -)
        elif line.startswith('-'):
            if hunk_start + hunk_offset < len(result_lines):
                # Remove this line
                result_lines.pop(hunk_start + hunk_offset)
            current_line += 1
            continue

        # Added line (starts with +)
        elif line.startswith('+'):
            # Insert new line
            result_lines.insert(hunk_start + hunk_offset, line[1:])
            hunk_offset += 1
            current_line += 1
            continue

        # Context line (starts with ' ' or is empty)
        else:
            # Skip context lines but increment the line counter
            if line.startswith(' '):
                line = line[1:]  # Remove the leading space
            hunk_offset += 1
            current_line += 1

    return '\n'.join(result_lines)

async def write_with_confirmation(app, filepath, content, code_processor):
    """
    Writes content to a temporary file, shows diff, and asks for user confirmation
    before writing to the actual file.

    Args:
        app: The Application instance
        filepath (str): Path to the file to write to
        content (list or str): Content to write to the file
        code_processor: The CodeProcessor instance managing the task

    Returns:
        Tuple of (result, message):
            - result: 'yes', 'no', 'request_change', 'edit', or 'accept_all'
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
        display_diff(app, diff)

        while True:
            # Ask for confirmation using the app's UI
            response, message = await app.ui.prompt_for_confirmation("Apply these changes?", diff_lines=diff)

            if response == 'yes':
                # Copy temp file to destination
                directory = os.path.dirname(filepath)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                shutil.copy2(temp_file_path, filepath)
                logger.info(f"Changes applied to {filepath}")
                return 'yes', None
            elif response == 'no':
                logger.info(f"Changes to {filepath} discarded")
                return 'no', None
            elif response == 'request_change':
                logger.info(f"Changes to {filepath} not applied, feedback requested")
                return 'request_change', message
            elif response == 'accept_all':
                # Set the flag on the code processor
                code_processor._accept_all_active = True
                # Copy temp file to destination
                directory = os.path.dirname(filepath)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                shutil.copy2(temp_file_path, filepath)
                logger.info(f"Changes applied to {filepath} (Accept All)")
                return 'accept_all', None
            elif response == 'edit':
                marked_content = apply_diff_markup(original_content, diff)

                # Open the editor using the UI wrapper
                edited_content_list = await app.ui.prompt_for_text_edit(marked_content, "Edit the proposed changes:")

                if edited_content_list is not None: # User saved, not cancelled
                    content_changed = edited_content_list != marked_content
                    if content_changed:
                        # The user saved changes in the editor
                        try:
                            # Clean markers and display whitespace from edited content
                            new_content_lines = []

                            for i, line_content in enumerate(edited_content_list):
                                cleaned_line = line_content
                                # line does not need to have \n on it
                                if cleaned_line.endswith("\n"):
                                    cleaned_line = cleaned_line.strip("\n")

                                # strip out added space, +, or -
                                if cleaned_line.startswith(" ") or cleaned_line.startswith("+"):
                                    new_content_lines.append(cleaned_line[1:])
                                elif cleaned_line.startswith("-"):
                                    # this is a deletion, remove the line don't add the line
                                    pass
                                else:
                                    # user may have deleted space in front, just add raw line as default
                                    new_content_lines.append(cleaned_line)

                            new_content_str = "\n".join(new_content_lines)
                            logger.info(f"Processed edited content into {len(new_content_lines)} lines")

                            # Write the new content to a new temp file
                            with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as new_temp_file:
                                new_temp_path = new_temp_file.name
                                new_temp_file.write(new_content_str)

                            # Generate a new diff to show the user what will be applied
                            new_diff = list(unified_diff(
                                original_lines,
                                new_content_str.splitlines(True),
                                fromfile=f'a/{filepath}',
                                tofile=f'b/{filepath}',
                                n=3
                            ))

                            # Show the new diff
                            app.ui.print_text("Updated changes:", PrintType.HEADER)
                            display_diff(app, new_diff)

                            # Update the temp file path to the new one
                            os.unlink(temp_file_path)
                            temp_file_path = new_temp_path

                            # Continue the loop to prompt again with the updated diff
                            app.ui.print_text("Edited changes prepared. Please confirm:", PrintType.INFO)
                            # Update the main diff for the next confirmation prompt
                            diff = new_diff 
                        except Exception as e:
                            app.ui.print_text(f"Error processing edited changes: {str(e)}", PrintType.ERROR)
                        continue # Continue the confirmation loop
                    else: # No changes were made
                        app.ui.print_text("No changes were made in the editor.", PrintType.INFO)
                        continue # Continue the confirmation loop
                else: # User cancelled the edit (edited_content_list is None)
                    app.ui.print_text("Edit cancelled.", PrintType.WARNING)
                    continue # Continue the confirmation loop

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    return 'no', None # Default return if loop exits unexpectedly


async def apply_file_changes(app, changes_json, code_processor):
    """
    Apply changes to files based on the provided JSON.

    Args:
        app: The Application instance
        changes_json: The JSON object containing changes
        code_processor: The CodeProcessor instance managing the task

    Returns:
        Dict: {'success': bool, 'files_changed': list, 'change_requested': Optional[str]}

    Raises:
        CodeTaskCancelled: If the user cancels the task during confirmation.
    """
    # Group changes by filename
    changes_by_file = {}
    new_files = []
    files_changed = []

    valid_operations = ["ADD", "DELETE", "REPLACE", "NEW", "RENAME"]

    for change in changes_json["changes"]:
        if "operation" not in change:
            logger.error(f"apply_file_changes: malformed change request: {change}")
            continue

        operation = change["operation"]
        if operation not in valid_operations:
            logger.warning(f"apply_file_changes: malformed change request, bad operation: {operation}")
            if operation == "MODIFY":
                operation = "REPLACE"
                logger.warning("switching MODIFY to REPLACE")
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
                logger.error(f"File not found: {filepath}")
                continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
            continue
        except Exception as e:
            logger.error(f"Error reading {filepath}: {str(e)}")
            continue

        # Process change operations
        new_lines = []
        try:
            new_lines = process_operation_changes(lines, changes, filepath)
        except KeyError as e:
            logger.info(f"Key error: {e}")
            return {"success": False}
        except ValueError as e:
            logger.info(f"Type error {e}")
            return {"success": False}
        except Exception as e:
            logger.info(f"failed to process_operation_changes {e}")
            return {"success": False}

        # Check if 'Accept All' is active
        if code_processor._accept_all_active:
            try:
                # Apply change directly without confirmation
                content_str = ''.join(new_lines)
                directory = os.path.dirname(filepath)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                # Write directly to the file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content_str)
                files_changed.append(filepath)
                message = f"Updated {filepath} (Accept All)"
                logger.info(message)
                app.ui.print_text(message, PrintType.SUCCESS)
            except Exception as e:
                logger.error(f"Error applying change directly to {filepath}: {e}")
                app.ui.print_text(f"Error applying change to {filepath}: {e}", PrintType.ERROR)
                # Decide if we should stop or continue? For now, continue.
        else:
            # Write the updated lines to a temp file, show diff, and ask for confirmation
            result, user_message = await write_with_confirmation(app, filepath, new_lines, code_processor)

            if result == 'yes':
                files_changed.append(filepath)
                message = f"Updated {filepath}"
                logger.info(message)
            elif result == 'accept_all':
                code_processor._accept_all_active = True # Ensure flag is set for subsequent steps
                files_changed.append(filepath)
                message = f"Updated {filepath} (Accept All activated)"
                logger.info(message)
                app.ui.print_text(message, PrintType.SUCCESS)
            elif result == 'no':
                logger.info(f"Update to {filepath} was cancelled by user")
                raise CodeTaskCancelled(f"User cancelled code task while updating {filepath}")
            elif result == 'request_change':
                logger.info(f"Update to {filepath} was not applied. User requested changes: {user_message}")
                return {"success": False, "change_requested": user_message}
            # 'edit' case is handled within write_with_confirmation, which loops until another choice is made

    # Process new file creations
    for change in new_files:
        if "filename" not in change:
            raise Exception(f"filename not in change: {change}")
        if "new_content" not in change:
            raise Exception(f"new_content not in change: {change}")

        filepath = change["filename"]
        new_content = change["new_content"]

        # Create directories if they don't exist
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            message = f"Created directory: {directory}"
            app.ui.print_text(message, PrintType.INFO)
            logger.info(message)

        # Check if 'Accept All' is active
        if code_processor._accept_all_active:
            try:
                # Write the new file directly
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                files_changed.append(filepath)
                message = f"Created new file: {filepath} (Accept All)"
                logger.info(message)
                app.ui.print_text(message, PrintType.SUCCESS)
            except Exception as e:
                logger.error(f"Error creating file directly {filepath}: {e}")
                app.ui.print_text(f"Error creating file {filepath}: {e}", PrintType.ERROR)
        else:
            # Write the new file with confirmation
            result, user_message = await write_with_confirmation(app, filepath, new_content, code_processor)

            if result == 'yes':
                files_changed.append(filepath)
                message = f"Created new file: {filepath}"
                logger.info(message)
            elif result == 'accept_all':
                code_processor._accept_all_active = True # Ensure flag is set for subsequent steps
                files_changed.append(filepath)
                message = f"Created new file: {filepath} (Accept All activated)"
                logger.info(message)
                app.ui.print_text(message, PrintType.SUCCESS)
            elif result == 'no':
                logger.info(f"Creation of {filepath} was cancelled by user")
                raise CodeTaskCancelled(f"User cancelled code task while creating {filepath}")
            elif result == 'request_change':
                logger.info(f"Creation of {filepath} was not applied. User requested changes: {user_message}")
                return {"success": False, "change_requested": user_message}
            # 'edit' case handled within write_with_confirmation

    return {"success": True, "files_changed": files_changed}

def process_operation_changes(lines, operation_changes, filepath):
    """
    Process changes based on operation (ADD/DELETE) and start_line.

    Args:
        lines: List of file lines
        operation_changes: List of changes with operation and start_line
        filepath: Name of the file being modified

    Returns:
        Updated list of lines
    """

    # Sort changes in descending order of start_line
    logger.info(f"process_operation_changes")

    for change in operation_changes:
        operation = change.get("operation")

        if operation is None:
            logger.info(f"operation malformed: {change}")
            raise KeyError("operation")
        if "filename" not in change:
            logger.info(f"filename not in change: {change}")
            raise KeyError("filename")

        # Process the operation based on its type
        if operation == "ADD":
            if "new_content" not in change:
                logger.info(f"new_content not in change: {change}")
                raise KeyError("new_content")

            lines = process_add_operation(lines, change, filepath)
        elif operation == "DELETE":
            lines = process_delete_operation(lines, change)
        elif operation == "REPLACE":
            lines = process_replace_operation(lines, change, filepath)

    return lines
