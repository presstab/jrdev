import os
import shutil
import tempfile
import logging
from typing import Optional # For Python < 3.9, use Optional[str]. For >=3.9, str | None

logger = logging.getLogger("jrdev")

class TempFileManagerError(Exception):
    """Base exception for errors related to TempFile management."""
    pass

class TempFileCreationError(TempFileManagerError):
    """Raised when temporary file creation fails."""
    pass

class TempFileOperationError(TempFileManagerError):
    """Raised for errors during operations like save or overwrite if not creation."""
    pass

class TempFileAccessError(TempFileManagerError):
    """Raised when trying to access a temp file that isn't properly initialized or has been cleaned up."""
    pass


class TemporaryFile:
    """
    Manages a temporary file
    """

    def __init__(self, initial_content: str = ""):
        """
        Initializes the TemporaryFile by creating a physical temporary file with initial_content.
        """
        self.path: str = self._create_new_file_with_content(initial_content)

    def _create_new_file_with_content(self, content: str) -> str:
        """
        Core logic to create a new temporary file, write content, and return its path.
        The created file handle is closed after writing.
        """
        tf = None
        try:
            tf = tempfile.NamedTemporaryFile(
                delete=False, mode='w', encoding='utf-8', suffix=".jrdev_tmp"
            )
            tf.write(content)
            created_path = tf.name
            return created_path
        except Exception as e:
            # If creation fails, try to clean up if a file was partially made
            if tf and tf.name and os.path.exists(tf.name):
                try:
                    os.unlink(tf.name)
                except OSError as unlink_err:
                    logger.error(f"Failed to unlink partially created temp file {tf.name} after error: {unlink_err}")
            logger.error(f"Failed to create temporary file: {e}", exc_info=True)
            raise TempFileCreationError(f"Failed to create temporary file: {e}") from e
        finally:
            if tf:
                tf.close() # Ensure file handle is closed

    def overwrite(self, new_content: str) -> None:
        """
        Replaces the current temporary file with a new one containing new_content.
        The old temporary file is unlinked.
        """
        old_path = self.path
        new_temp_path = None
        try:
            # Create the new temp file first
            new_temp_path = self._create_new_file_with_content(new_content)

            # If new file creation was successful, update self.path
            self.path = new_temp_path

            # Then, try to unlink the old file
            if old_path and os.path.exists(old_path):
                try:
                    os.unlink(old_path)
                except OSError as e:
                    # Log the error but proceed, as the new file is now primary.
                    logger.warning(f"Could not unlink old temp file {old_path} during overwrite: {e}")
        except TempFileCreationError: # Propagate creation error for the new file
            # If new file creation failed, self.path should remain the old_path.
            # new_temp_path would be None or the path of a file that failed creation (and should have been cleaned by _create_new_file_with_content)
            self.path = old_path # Ensure self.path is reverted if it was changed optimistically
            raise # Re-raise the TempFileCreationError
        except Exception as e:
            # Catch any other unexpected error during the overwrite logic
            self.path = old_path # Revert path if something else went wrong
            logger.error(f"Unexpected error during overwrite. Old path: {old_path}, New content attempted. Error: {e}", exc_info=True)
            raise TempFileOperationError(f"Unexpected error during overwrite: {e}") from e


    def save_to(self, destination_path: str) -> None:
        """
        Creates destination directories if they don't exist.
        """
        if not self.path or not os.path.exists(self.path):
            msg = f"Temporary file path '{self.path}' is invalid or file does not exist. Cannot save."
            logger.error(msg)
            raise TempFileAccessError(msg)

        try:
            directory = os.path.dirname(destination_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            shutil.copy2(self.path, destination_path)
            logger.info(f"Temporary file {self.path} successfully saved to {destination_path}")
        except Exception as e:
            logger.error(f"Error saving temp file {self.path} to {destination_path}: {e}", exc_info=True)
            raise TempFileOperationError(f"Failed to save temporary file to {destination_path}: {e}") from e

    def get_current_path(self) -> str:
        """Returns the path of the current temporary file."""
        if not self.path:
            # This should ideally not happen if __init__ was successful.
            msg = "Temporary file path is not set (TemporaryFile.path is None)."
            logger.error(msg)
            raise TempFileAccessError(msg)
        return self.path

    def cleanup(self) -> None:
        """
        Deletes the current temporary file from the filesystem.
        """
        if self.path and os.path.exists(self.path):
            try:
                os.unlink(self.path)
                logger.debug(f"Cleaned up temp file: {self.path}")
            except OSError as e:
                # Log error but don't re-raise from cleanup, as it's often called in __exit__.
                logger.error(f"Error unlinking temp file {self.path} during cleanup: {e}")
        self.path = None # Mark as cleaned up

    def __enter__(self):
        if not self.path: # Should be set by __init__
            raise TempFileAccessError("TemporaryFile entered but path is not initialized. __init__ might have failed.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()