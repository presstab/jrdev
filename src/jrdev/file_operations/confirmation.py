import os
import shutil
import tempfile
from difflib import unified_diff

from jrdev.file_operations.diff_markup import apply_diff_markup
from jrdev.ui.ui import display_diff, PrintType
import logging
logger = logging.getLogger("jrdev")

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
