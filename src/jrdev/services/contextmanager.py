#!/usr/bin/env python3

"""
Context manager for JrDev that manages file analyses.
"""

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

from jrdev.file_operations.file_utils import JRDEV_DIR
from jrdev.services.llm_requests import generate_llm_response
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.utils.string_utils import contains_chinese

# Create an asyncio lock for safe file access
context_file_lock = asyncio.Lock()

# Get the global logger instance
logger = logging.getLogger("jrdev")


class ContextManager:
    """
    Manages file context generation and caching for the JrDev application.
    This class handles per-file context storage and maintains an index of
    file hashes and modification times for efficient updates.
    """

    def __init__(self) -> None:
        """Initialize the context manager with an empty index."""
        self.index: Dict[str, Any] = {}  # In-memory cache of {file_path: metadata}

        jrdev_dir = JRDEV_DIR
        self.contexts_dir = os.path.join(jrdev_dir, "contexts")
        self.index_path = os.path.join(self.contexts_dir, "file_index.json")

        self.load_index()

    def load_index(self) -> None:
        """Load the context index from disk or create it if it doesn't exist."""
        # Create contexts directory if it doesn't exist
        try:
            # Create the base JRDEV_DIR first if needed, then the contexts directory
            os.makedirs(self.contexts_dir, exist_ok=True)
            logger.info(f"Ensured contexts directory exists at {self.contexts_dir}")
        except Exception as e:
            logger.error(f"Error creating contexts directory: {str(e)}")

        # Load index if it exists
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r") as f:
                    self.index = json.load(f)
                    logger.info(
                        f"Loaded context index with {len(self.index.get('files', {}))} entries"
                    )
            except Exception as e:
                logger.error(f"Error loading context index: {str(e)}")
                self.index = {"files": {}}
        else:
            # Initialize empty index
            self.index = {"files": {}}
            self.save_index()
            logger.info("Created new context index")

    def save_index(self) -> None:
        """Save the context index to disk."""
        try:
            with open(self.index_path, "w") as f:
                json.dump(self.index, f, indent=2)
            logger.info(
                f"Saved context index with {len(self.index.get('files', {}))} entries"
            )
        except Exception as e:
            logger.error(f"Error saving context index: {str(e)}")

    def _path_to_filename(self, file_path: str) -> str:
        return file_path.replace("/", "-@-")

    def _filename_to_path(self, filename: str) -> str:
        return filename.replace("-@-", "/")

    def get_context_path(self, file_path: str) -> str:
        """
        Get the path to the context file for a given file.

        Args:
            file_path: Path to the source file

        Returns:
            Path to the context file
        """
        # Remove leading ./ if present
        if file_path.startswith("./"):
            file_path = file_path[2:]

        # Convert file path to filename using the conversion method
        filename = self._path_to_filename(file_path) + ".md"
        context_file_path = os.path.join(self.contexts_dir, filename)

        # Create the directory if it doesn't exist
        parent_dir = os.path.dirname(context_file_path)
        os.makedirs(parent_dir, exist_ok=True)

        return context_file_path

    def _get_file_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate MD5 hash of a file's contents.

        Args:
            file_path: Path to the file

        Returns:
            MD5 hash of the file contents or None if file doesn't exist
        """
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            return None

    def read_context_file(self, file_path: str) -> str:
        """
        Read the context file for a given source file.

        Args:
            file_path: Path to the source file

        Returns:
            Contents of the context file or empty string if it doesn't exist
        """
        context_path = self.get_context_path(file_path)

        try:
            if os.path.exists(context_path):
                with open(context_path, "r") as f:
                    return f.read()
            return ""
        except Exception as e:
            logger.error(f"Error reading context file {context_path}: {str(e)}")
            return ""

    def needs_update(self, file_path: str) -> bool:
        """
        Check if a file's context needs to be updated based on hash and modification time.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file's context needs updating, False otherwise
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return False

        # Get current file stats
        current_hash = self._get_file_hash(file_path)
        last_modified = os.path.getmtime(file_path)

        # Check if file is in the index
        files_index = self.index.get("files", {})
        if file_path not in files_index:
            logger.info(f"File not in index, needs update: {file_path}")
            return True

        # Get saved file stats
        file_info = files_index[file_path]
        saved_hash = file_info.get("hash")
        saved_modified = file_info.get("last_modified")

        # Check if hash or modification time has changed
        if current_hash != saved_hash or abs(last_modified - saved_modified) > 1:
            logger.info(f"File changed, needs update: {file_path}")
            return True

        # Check if context file exists - using stored filename from index
        context_filename = file_info.get("context_path")
        if not context_filename or not os.path.exists(
            os.path.join(self.contexts_dir, context_filename)
        ):
            logger.info(f"Context file missing, needs update: {file_path}")
            return True

        return False

    async def get_context(self, file_path: str) -> str:
        """
        Get cached context or generate new context for a file.

        Args:
            file_path: Path to the file

        Returns:
            Context for the file
        """
        if self.needs_update(file_path):
            logger.info(f"Generating new context for {file_path}")
            await self.generate_context(file_path)
        else:
            logger.info(f"Using cached context for {file_path}")

        return self.read_context_file(file_path)

    async def generate_context(
        self,
        file_path: str,
        app: Any = None,
        additional_context: Optional[List[str]] = None,
        task_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate context for a file using an LLM and cache it.

        Args:
            file_path: Path to the file to analyze
            app: The Application instance
            additional_context: Optional additional context for the LLM
            task_id: Optional task ID for UI tracking

        Returns:
            Generated context or None if an error occurred
        """
        if additional_context is None:
            additional_context = []

        if not app:
            logger.error("Application instance is required for generate_context")
            return None

        # Handle file path as string or list
        files: List[str]
        if isinstance(file_path, list):
            files = file_path
        else:
            files = [file_path]

        # Read the file content
        try:
            full_content = ""
            for file in files:
                # check existence
                if not os.path.exists(file):
                    logger.error(f"\nFile not found: {file}")
                    return None

                with open(file, "r") as f:
                    file_content = f.read()

                # Limit file size
                if len(file_content) > 2000 * 1024:
                    size_mb = len(file_content) / (1024 * 1024)
                    error_msg = f"File {file} is too large ({size_mb:.2f} MB) for context generation (max: 2MB)"
                    logger.error(error_msg)
                    return None

                full_content += f"{file_content}"

            # Get prompt from the prompt manager
            text_prompt = PromptManager.load("file_analysis")

            # Create a new chat thread for each file
            temp_messages: List[Dict[str, str]] = [
                {"role": "system", "content": text_prompt},
                {"role": "user", "content": full_content},
            ]
            if len(additional_context) > 0:
                temp_messages.append(
                    {"role": "assistant", "content": str(additional_context)}
                )

            logger.info(f"Waiting for LLM analysis of {file_path}...")

            # Send the request to the LLM
            file_analysis_result: Any = await generate_llm_response(
                app, app.state.model, temp_messages, task_id=task_id, print_stream=False, max_output_tokens=500
            )
            file_analysis = str(file_analysis_result)
            if contains_chinese(file_analysis):
                logger.error(f"Malformed file analysis for {file_path}: detected Chinese characters:\n{file_analysis}")
                return None

            # Print the analysis
            logger.info(f"\nFile Analysis for {file_path}:")
            logger.info(file_analysis)

            # Get context file path and create parent directories if needed
            # For multiple files, always use the first file as the primary file for context storage
            primary_file = file_path if isinstance(file_path, str) else file_path[0]
            context_file_path = self.get_context_path(primary_file)

            # Ensure the directory exists for the context file
            context_dir = os.path.dirname(context_file_path)
            os.makedirs(context_dir, exist_ok=True)

            # Update the context file safely with a lock
            logger.info(f"Writing context to file: {context_file_path}")
            try:
                async with context_file_lock:
                    with open(context_file_path, "w") as context_file:
                        if len(files) > 1:
                            # For file pairs, note that this contains analysis of multiple files
                            file_list_str = ", ".join(files)
                            context_file.write(
                                f"# Analysis for files: {file_list_str}\n\n"
                            )
                        else:
                            context_file.write(f"# Analysis for {primary_file}\n\n")
                        context_file.write(f"{file_analysis}\n\n")
                logger.info(f"Successfully wrote context to: {context_file_path}")
            except Exception as e:
                logger.error(f"Error writing context file {context_file_path}: {str(e)}")

            # Update the index with the new file information - always track the primary file
            self.track_file(primary_file)

            logger.info(f"\nFile analysis complete. Results saved to {context_file_path}")
            return str(file_analysis)

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return None

    def track_file(self, file_path: str) -> None:
        """
        Add a file to the index with its current state.

        Args:
            file_path: Path to the file to track
        """
        if not os.path.exists(file_path):
            logger.warning(f"Cannot track non-existent file: {file_path}")
            return

        # Get current file stats
        current_hash = self._get_file_hash(file_path)
        last_modified = os.path.getmtime(file_path)

        # Remove leading ./ if present
        if file_path.startswith("./"):
            file_path = file_path[2:]

        # Create filename using the conversion method
        filename = self._path_to_filename(file_path) + ".md"

        # Update the index
        if "files" not in self.index:
            self.index["files"] = {}

        self.index["files"][file_path] = {
            "hash": current_hash,
            "last_modified": last_modified,
            "context_path": filename,
        }

        # Save the updated index
        self.save_index()
        logger.info(f"Added {file_path} to context index")

    def get_outdated_files(self) -> List[str]:
        """
        Check which files in the index need their context updated.

        Returns:
            List of file paths that need updating
        """
        outdated_files = []

        for file_path in self.index.get("files", {}):
            if os.path.exists(file_path) and self.needs_update(file_path):
                outdated_files.append(file_path)

        return outdated_files

    def get_file_paths(self) -> List[str]:
        obj_files = self.index.get("files", {})
        return list(obj_files.keys())

    def get_index_paths(self) -> List[List[str]]:
        """
        Get relative paths of all indexes in the context manager.

        Returns:
            Dict of index file path -> indexed file path (ie the real file that was indexed)
        """
        indexes_list = []
        for file_path in self.index.get("files", {}):
            context_path = self.get_context_path(file_path)
            indexes_list.append([context_path, str(file_path)])
        return indexes_list

    def get_all_context(self) -> str:
        """
        Get all context files combined into a single string.

        Returns:
            Combined context from all tracked files
        """
        contexts = []
        for file_path in self.index.get("files", {}):
            context = self.read_context_file(file_path)
            if context:  # Only include if there's actual content
                contexts.append(f"## {file_path} BEGIN ##\n{context}\n ## {file_path} END ##\n")

        if not contexts:
            return ""

        return "\n\n".join(contexts)

    def get_context_for_files(self, file_paths: List[str]) -> str:
        """
        Get context for specific files combined into a single string.

        Args:
            file_paths: List of file paths to get context for

        Returns:
            Combined context from the specified files
        """
        if not file_paths:
            return ""

        contexts = []
        for file_path in file_paths:
            # Skip files that don't exist in the index
            if file_path not in self.index.get("files", {}):
                logger.info(f"No context found for file: {file_path}")
                continue

            context = self.read_context_file(file_path)
            if context:  # Only include if there's actual content
                contexts.append(f"## {file_path}\n{context}")

        if not contexts:
            return ""

        return "\n\n".join(contexts)

    def batch_update_contexts(
        self, app: Any, file_paths: List[str], concurrency: int = 5, worker_id: Optional[str] = None
    ) -> asyncio.Future[List[Optional[str]]]:
        """
        Update contexts for multiple files concurrently.

        Args:
            app: The Application instance
            file_paths: List of file paths to update
            concurrency: Maximum number of concurrent updates
            worker_id: Optional task ID for UI tracking

        Returns:
            Future that resolves when all updates are complete
        """

        async def _process_batch() -> List[Optional[str]]:
            semaphore = asyncio.Semaphore(concurrency)

            async def _process_file(index: int, file_path: str, worker_id: Optional[str]) -> Optional[str]:
                async with semaphore:
                    # Add a small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

                    sub_task_id = None
                    if worker_id:
                        sub_task_id = f"{worker_id}:{index}"
                        app.ui.update_task_info(worker_id, update={"new_sub_task": sub_task_id, "description": f"Update: {file_path}"})
                        logger.info(f"Starting context update for sub-task {sub_task_id}: {file_path}")

                    result = await self.generate_context(file_path, app, task_id=sub_task_id)

                    if worker_id and sub_task_id:
                        app.ui.update_task_info(sub_task_id, update={"sub_task_finished": True})
                        logger.info(f"Finished context update for sub-task {sub_task_id}: {file_path}")

                    return result

            tasks = [_process_file(i, file_path, worker_id) for i, file_path in enumerate(file_paths)]
            results = await asyncio.gather(*tasks)
            # Explicitly cast to ensure correct type
            return [result for result in results]

        # Return the future to allow callers to await it
        return asyncio.create_task(_process_batch())
