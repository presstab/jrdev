import os
from typing import Optional

from jrdev.file_operations.diff_markup import apply_diff_markup, remove_diff_markup
from jrdev.file_operations.diff_utils import create_diff
from jrdev.file_operations.temp_file import TemporaryFile, TempFileOperationError, TempFileManagerError, \
    TempFileCreationError, TempFileAccessError
from jrdev.ui.ui import display_diff, PrintType
import logging
logger = logging.getLogger("jrdev")


async def write_with_confirmation(app, filepath: str, content: list | str, code_processor):
    if isinstance(content, list):
        content_str = ''.join(content)
    else:
        content_str = content

    # temporary_file will be None if TempFile.__init__ fails and an exception is caught by the outer try-except
    temporary_file: Optional[TemporaryFile] = None
    error_msg = None
    try:
        with TemporaryFile(initial_content=content_str) as temporary_file:
            original_content = ""
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                except IOError as e:  # More specific exception for file reading
                    logger.error(f"Error reading original file {filepath}: {e}", exc_info=True)
                    app.ui.print_text(f"Error reading original file {filepath}: {e}", PrintType.ERROR)
                    return 'no', None  # Cannot proceed without original content for diff

            # Initial content for diff is what was written to the temp file
            current_diff_content = content_str
            diff = create_diff(original_content, current_diff_content, filepath)
            display_diff(app, diff)

            while True:
                response, message = await app.ui.prompt_for_confirmation("Apply these changes?", diff_lines=diff, error_msg=error_msg)
                error_msg = None

                if response == 'yes':
                    try:
                        temporary_file.save_to(filepath)
                        logger.info(f"Changes applied to {filepath}")
                        return 'yes', None
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

                elif response == 'accept_all':
                    code_processor._accept_all_active = True
                    try:
                        temporary_file.save_to(filepath)
                        logger.info(f"Changes applied to {filepath} (Accept All)")
                        return 'accept_all', None
                    except TempFileOperationError as e:
                        logger.error(f"Failed to save changes (accept_all) to {filepath}: {e}", exc_info=True)
                        app.ui.print_text(f"Error applying changes (accept_all): {e}", PrintType.ERROR)
                        error_msg = "Failed to write file to disk. See log for more detail."
                        continue

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

                    # content_changed is True
                    try:
                        new_edited_content_str = remove_diff_markup(edited_content_list)

                        # Overwrite the temp file. This can raise TempFileManagerError.
                        temporary_file.overwrite(new_edited_content_str)

                        current_diff_content = new_edited_content_str  # Update for next diff
                        new_diff = create_diff(original_content, current_diff_content, filepath)
                        logger.info(f"Diff after user edits:\n{new_diff}") # Already logged by display_diff

                        app.ui.print_text("Updated changes:", PrintType.HEADER)  # Give feedback before display
                        display_diff(app, new_diff)  # Display the new diff
                        app.ui.print_text("Edited changes prepared. Please confirm:", PrintType.INFO)
                        diff = new_diff
                    except TempFileManagerError as e:  # Catch specific errors from overwrite
                        logger.error(f"Error processing edited changes (temp file op): {e}", exc_info=True)
                        app.ui.print_text(f"Error processing edited changes: {e}", PrintType.ERROR)
                        error_msg = "Error processing file changes. See log for more detail."
                        # Loop continues, user sees error, can try again or choose another option.
                    except Exception as e:  # Catch other errors (e.g., from remove_diff_markup)
                        logger.error(f"Unexpected error processing edited changes: {e}", exc_info=True)
                        app.ui.print_text(f"An unexpected error occurred while processing edits: {str(e)}",
                                          PrintType.ERROR)
                        error_msg = "An unexpected error occurred. See log for more detail."
                    continue  # Always continue the loop after an edit attempt (success or failure)
                    # to allow user to re-confirm or choose another option.
                # else: # Should not be reached with current UI logic
                #     logger.warning(f"Unexpected response from confirmation: {response}")
                #     return 'no', None # Safety return

    except TempFileCreationError as e:  # Catches error from TempFile.__init__
        logger.error(f"Failed to initialize temporary file system for {filepath}: {e}", exc_info=True)
        app.ui.print_text(f"Error setting up temporary file system: {e}", PrintType.ERROR)
        # temporary_file is likely None or partially formed, 'with' statement's __exit__ won't run if __enter__ failed.
        # No explicit cleanup needed here as 'with' handles it if __enter__ succeeded.
        return 'no', None
    except TempFileAccessError as e:  # Should be rare if using 'with' correctly, but good for defense
        logger.error(f"Critical TempFile access error for {filepath}: {e}", exc_info=True)
        app.ui.print_text(f"A critical error occurred with temporary file management: {e}", PrintType.ERROR)
        return 'no', None
    except Exception as e:  # Catch-all for other unexpected errors in the main flow
        logger.error(f"Unexpected error in write_with_confirmation for {filepath}: {e}", exc_info=True)
        app.ui.print_text(f"An unexpected error occurred: {e}", PrintType.ERROR)
        # If temporary_file was successfully created and entered the 'with' block,
        # its __exit__ (cleanup) will be called automatically even if an exception occurs within the 'with' block.
        return 'no', None

    # This part should ideally not be reached if the loop logic is complete and returns explicitly.
    # If the while loop is broken out of without a return, this will be the default.
    logger.warning(f"write_with_confirmation exited unexpectedly for {filepath}.")
    return 'no', None