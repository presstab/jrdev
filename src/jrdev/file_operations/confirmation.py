import os
from typing import Optional, Tuple

from jrdev.file_operations.diff_markup import apply_diff_markup, remove_diff_markup
from jrdev.file_operations.diff_utils import create_diff
from jrdev.file_operations.temp_file import TemporaryFile, TempFileOperationError, TempFileManagerError, \
    TempFileCreationError, TempFileAccessError
from jrdev.ui.ui import display_diff, PrintType
import logging
logger = logging.getLogger("jrdev")


async def write_file_with_confirmation(app, filepath: str, content: str):
    """
    A reusable function to write content to a file with user confirmation.
    This function is decoupled from the CodeProcessor and can be used by agent tools.
    Returns the user's choice and any message.
    """
    original_content = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except IOError as e:
            logger.error(f"Error reading original file {filepath}: {e}", exc_info=True)
            app.ui.print_text(f"Error reading original file {filepath}: {e}", PrintType.ERROR)
            return 'no', None

    error_msg = None
    try:
        with TemporaryFile(initial_content=content) as temp_file:
            current_diff_content = content
            diff = create_diff(original_content, current_diff_content, filepath)
            display_diff(app, diff)

            while True:
                response, message = await app.ui.prompt_for_confirmation("Apply these changes?", diff_lines=diff, error_msg=error_msg)
                error_msg = None

                if response in ['yes', 'accept_all']:
                    try:
                        temp_file.save_to(filepath)
                        logger.info(f"Changes applied to {filepath}")
                        return response, None
                    except TempFileOperationError as e:
                        logger.error(f"Failed to save changes to {filepath}: {e}", exc_info=True)
                        app.ui.print_text(f"Error applying changes: {e}", PrintType.ERROR)
                        error_msg = "Failed to write file to disk. See log for more detail."
                        continue
                
                elif response == 'no':
                    logger.info(f"Changes to {filepath} discarded")
                    return 'no', None

                elif response == 'request_change':
                    logger.info(f"Changes to {filepath} not applied, feedback requested")
                    return 'request_change', message

                elif response == 'edit':
                    marked_content = apply_diff_markup(original_content, diff)
                    edited_content_list = await app.ui.prompt_for_text_edit(marked_content,
                                                                            "Edit the proposed changes:")

                    if not edited_content_list:
                        app.ui.print_text("Edit cancelled.", PrintType.WARNING)
                        continue

                    content_changed = edited_content_list != marked_content
                    if not content_changed:
                        app.ui.print_text("No changes were made in the editor.", PrintType.INFO)
                        continue
                    
                    try:
                        new_edited_content_str = remove_diff_markup(edited_content_list)
                        temp_file.overwrite(new_edited_content_str)
                        current_diff_content = new_edited_content_str
                        diff = create_diff(original_content, current_diff_content, filepath)
                        display_diff(app, diff)
                        app.ui.print_text("Edited changes prepared. Please confirm:", PrintType.INFO)
                    except Exception as e:
                        logger.error(f"Unexpected error processing edited changes: {e}", exc_info=True)
                        app.ui.print_text(f"An unexpected error occurred while processing edits: {str(e)}",
                                          PrintType.ERROR)
                        error_msg = "An unexpected error occurred. See log for more detail."
                    continue
    except (TempFileCreationError, TempFileAccessError, TempFileManagerError) as e:
        logger.error(f"File operation error for {filepath}: {e}", exc_info=True)
        app.ui.print_text(f"Error during file operation: {e}", PrintType.ERROR)
        return 'no', None
    
    return 'no', None


async def write_with_confirmation(app, filepath: str, content: list | str) -> Tuple[str, str]:
    if isinstance(content, list):
        content_str = ''.join(content)
    else:
        content_str = content

    return await write_file_with_confirmation(app, filepath, content_str)
