import os

from jrdev.file_operations.add import process_add_operation
from jrdev.file_operations.confirmation import write_with_confirmation
from jrdev.file_operations.delete import process_delete_operation
from jrdev.core.exceptions import CodeTaskCancelled
from jrdev.file_operations.replace import process_replace_operation
from jrdev.file_operations.file_utils import find_similar_file
from jrdev.ui.ui import PrintType
import logging
logger = logging.getLogger("jrdev")

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

    valid_operations = ["ADD", "DELETE", "REPLACE", "WRITE", "RENAME"]

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
        if operation == "WRITE":
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
        if code_processor.accept_all_active:
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
            result, user_message = await write_with_confirmation(app, filepath, new_lines)

            if result == 'yes':
                files_changed.append(filepath)
                message = f"Updated {filepath}"
                logger.info(message)
            elif result == 'accept_all':
                code_processor.accept_all_active = True # Ensure flag is set for subsequent steps
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
        if code_processor.accept_all_active:
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
            result, user_message = await write_with_confirmation(app, filepath, new_content)

            if result == 'yes':
                files_changed.append(filepath)
                message = f"Created new file: {filepath}"
                logger.info(message)
            elif result == 'accept_all':
                code_processor.accept_all_active = True # Ensure flag is set for subsequent steps
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
