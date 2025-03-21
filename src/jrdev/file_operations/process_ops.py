import logging
import os
import tempfile
from difflib import unified_diff
import shutil
import platform
import re

from jrdev.ui.ui import terminal_print, PrintType, display_diff, prompt_for_confirmation
from jrdev.ui.diff_editor import curses_editor
from jrdev.file_operations.add import process_add_operation
from jrdev.file_operations.delete import process_delete_operation
from jrdev.file_operations.replace import process_replace_operation
from jrdev.file_operations.insert import process_insert_after_changes
from jrdev.file_utils import find_similar_file

# Get the global logger instance
logger = logging.getLogger("jrdev")


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
                
                # Display the full file content instead of just the diff
                full_content_lines = original_content.splitlines()
                
                # Add diff markers to show which lines would be changed
                diff_markers = {}
                line_offset = 0
                hunk_start = None
                
                # Debug information
                terminal_print(f"Processing diff with {len(diff)} lines", PrintType.INFO)
                
                # First pass: Parse the diff to understand where changes are
                current_line = 0
                hunk_data = []  # Store all parsed hunks for better processing
                
                # Parse all hunks from the diff
                while current_line < len(diff):
                    line = diff[current_line]
                    
                    # Skip header lines
                    if line.startswith('---') or line.startswith('+++') or line.startswith('diff'):
                        current_line += 1
                        continue
                    
                    # New hunk - extract line numbers
                    if line.startswith('@@'):
                        match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line)
                        if match:
                            old_start, old_count, new_start, new_count = map(int, match.groups())
                            hunk_start = old_start - 1  # 0-based indexing
                            
                            # Start tracking a new hunk
                            current_hunk = {
                                'start': hunk_start,
                                'old_count': old_count,
                                'lines': []
                            }
                            
                            # Read all lines in this hunk and store them
                            current_line += 1
                            while current_line < len(diff) and not diff[current_line].startswith('@@'):
                                current_hunk['lines'].append(diff[current_line])
                                current_line += 1
                            
                            # Store the completed hunk
                            hunk_data.append(current_hunk)
                            continue
                        else:
                            # Invalid hunk format, skip this line
                            current_line += 1
                            continue
                    
                    # Any other line, just skip
                    current_line += 1
                
                # Process all hunks to build diff markers
                for hunk in hunk_data:
                    hunk_start = hunk['start']
                    line_offset = 0
                    
                    # Process each line in the hunk
                    for line in hunk['lines']:
                        # Deleted line (starts with -)
                        if line.startswith('-'):
                            position = hunk_start + line_offset
                            if 0 <= position < len(full_content_lines):
                                diff_markers[position] = "delete"
                            line_offset += 1
                        
                        # Added line (starts with '+')
                        elif line.startswith('+'):
                            position = hunk_start + line_offset
                            # If we have a corresponding deletion, this is a replacement
                            if position in diff_markers and diff_markers[position] == "delete":
                                # This is a replacement (delete old, add new)
                                diff_markers[position] = ("replace", line[1:])
                            else:
                                # This is a new line to be added
                                if position >= len(full_content_lines):
                                    # Append to the end
                                    full_content_lines.append("+" + line[1:])
                                else:
                                    # Insert before the current line
                                    diff_markers[position] = ("add", line[1:])
                            line_offset += 1
                        
                        # Context line (may start with space or be empty)
                        elif len(line) > 0 and line[0] == ' ':
                            # Regular context line
                            line_offset += 1
                        else:
                            # Skip other lines (e.g., empty lines, no-newline indicators)
                            line_offset += 1
                            pass
                
                # Second pass: Prepare the content with markers
                marked_content = []
                insertions = {}  # Track insertions: {line_idx: [lines to insert before this line]}

                # First handle insertions separately to avoid messing up indices
                for idx in diff_markers:
                    marker = diff_markers[idx]
                    if isinstance(marker, tuple) and marker[0] == "add":
                        # Store lines to be inserted
                        if idx not in insertions:
                            insertions[idx] = []
                        insertions[idx].append("+" + marker[1])

                # insertions have to be added into hunks - todo probably a better way to do this above instead of reprocess?
                insertions_combined = {}
                current_start = None
                current_group = []
                prev_line = None

                for line_num in sorted(insertions.keys()):
                    if current_start is None:  # First entry
                        current_start = line_num
                        current_group = insertions[line_num].copy()
                        prev_line = line_num
                    elif line_num == prev_line + 1:  # Consecutive line number
                        current_group.extend(insertions[line_num])
                        prev_line = line_num
                    else:  # Non-consecutive, start new group
                        insertions_combined[current_start] = current_group
                        current_start = line_num
                        current_group = insertions[line_num].copy()
                        prev_line = line_num

                # Add the final group
                if current_start is not None:
                    insertions_combined[current_start] = current_group

                # Now process the content with markers
                for idx, line in enumerate(full_content_lines):

                    # First add any inserted lines before this position
                    if idx in insertions_combined:
                        for inserted_line in insertions_combined[idx]:
                            marked_content.append(inserted_line)

                    # Then handle the current line
                    if idx in diff_markers:
                        marker = diff_markers[idx]
                        if marker == "delete":
                            # Line to be deleted
                            marked_content.append("-" + line)
                        elif isinstance(marker, tuple):
                            if marker[0] == "replace":
                                # Show both the deleted line and the replacement line
                                marked_content.append("-" + line)  # Original line marked for deletion
                                marked_content.append("+" + marker[1])  # New line marked as addition
                            elif marker[0] == "add":
                                # content already inserted in the insertions above, now add original line content
                                marked_content.append(line)
                        else:
                            # Any other marker type - treat as unchanged
                            marked_content.append(" " + line)
                    else:
                        # Unchanged line
                        marked_content.append(" " + line)
                
                # Open the editor with the full marked content
                edited_content = curses_editor(marked_content)
                
                # Check if there were any actual changes made
                # Compare the content that was sent to the editor with what came back
                content_changed = edited_content != marked_content
                
                if edited_content and content_changed:
                    # The user saved changes in the editor
                    try:
                        # Clean markers and display whitespace from edited content
                        new_content_lines = []
                        
                        for i, line in enumerate(edited_content):
                            cleaned_line = line
                            # line does not need to have \n on it
                            if cleaned_line.endswith("\n"):
                                cleaned_line = cleaned_line.strip("\n")

                            # strip out added space, +, or -
                            if cleaned_line.startswith(" ") or cleaned_line.startswith("+") or cleaned_line.startswith("-"):
                                new_content_lines.append(cleaned_line[1:])
                            else:
                                # user may have deleted space in front, just add raw line as default
                                new_content_lines.append(cleaned_line)
                        
                        new_content_str = "\n".join(new_content_lines)
                        terminal_print(f"Processed edited content into {len(new_content_lines)} lines", PrintType.INFO)
                        
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
                        terminal_print("Updated changes:", PrintType.HEADER)
                        display_diff(new_diff)
                        
                        # Update the temp file path to the new one
                        os.unlink(temp_file_path)
                        temp_file_path = new_temp_path
                        
                        # Continue the loop to prompt again with the updated diff
                        terminal_print("Edited changes prepared. Please confirm:", PrintType.INFO)
                    except Exception as e:
                        terminal_print(f"Error applying diff: {str(e)}", PrintType.ERROR)
                        continue
                else:
                    # User quit without saving or no changes were made
                    if edited_content and not content_changed:
                        terminal_print("No changes were made in the editor.", PrintType.INFO)
                    else:
                        terminal_print("Edit cancelled.", PrintType.WARNING)
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