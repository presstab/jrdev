import glob
import json
import logging
import os
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jrdev.languages.utils import detect_language, is_headers_language
from jrdev.ui.ui import PrintType

# Base directory for jrdev files
JRDEV_DIR = ".jrdev/"

# Get the absolute path to the jrdev package directory
JRDEV_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JRDEV_ROOT_DIR = os.path.dirname(os.path.dirname(JRDEV_PACKAGE_DIR))  # Move up to the project root


# Get the global logger instance
logger = logging.getLogger("jrdev")


def requested_files(text) -> List[str]:
    match = re.search(r"get_files\s+(\[.*?\])", text, re.DOTALL)
    file_list = []
    if match:
        file_list_str = match.group(1)
        file_list_str = file_list_str.replace("'", '"')
        try:
            file_list = eval(file_list_str)
        except Exception as e:
            logger.error(f"Error parsing file list: {str(e)}")
            file_list = []

    if file_list == []:
        return file_list

    # Check if language has headers for classes, if so make sure both header and source file are included in files_to_send
    checked_files = set(file_list)
    additional_files = []

    for file in file_list:
        language = detect_language(file)
        if is_headers_language(language):
            base_name, ext = os.path.splitext(file)

            # If it's a header file (.h, .hpp), look for corresponding source file (.cpp, .cc)
            if ext.lower() in ['.h', '.hpp']:
                for source_ext in ['.cpp', '.cc', '.cxx', '.c++']:
                    source_file = f"{base_name}{source_ext}"
                    if os.path.exists(source_file) and source_file not in checked_files:
                        logger.info(f"Adding corresponding source file: {source_file}")
                        additional_files.append(source_file)
                        checked_files.add(source_file)
                        break

            # If it's a source file (.cpp, .cc), look for corresponding header file (.h, .hpp)
            elif ext.lower() in ['.cpp', '.cc', '.cxx', '.c++']:
                for header_ext in ['.h', '.hpp']:
                    header_file = f"{base_name}{header_ext}"
                    if os.path.exists(header_file) and header_file not in checked_files:
                        logger.info(f"Adding corresponding header file: {header_file}")
                        additional_files.append(header_file)
                        checked_files.add(header_file)
                        break

    # Add the additional files to the list
    file_list.extend(additional_files)
    return file_list


def find_similar_file(file_path):
    """
    Attempts to find a similar file when the exact path doesn't match.
    """
    original_filename = os.path.basename(file_path)
    original_dirname = os.path.dirname(file_path)

    # Strategy 1: Look for exact filename in any directory
    try:
        matches = []
        for root, _, files in os.walk('.'):
            if original_filename in files:
                matches.append(os.path.join(root, original_filename))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            matches.sort(key=lambda m: SequenceMatcher(None, os.path.dirname(m), original_dirname).ratio(), reverse=True)
            return matches[0]
    except Exception:
        pass

    # Strategy 2: Fuzzy matching in the same directory
    try:
        if os.path.exists(original_dirname):
            files_in_dir = [f for f in os.listdir(original_dirname) if os.path.isfile(os.path.join(original_dirname, f))]
            if files_in_dir:
                similar_files = sorted(files_in_dir, key=lambda f: SequenceMatcher(None, f, original_filename).ratio(), reverse=True)
                best_match = similar_files[0]
                if SequenceMatcher(None, best_match, original_filename).ratio() > 0.6:
                    return os.path.join(original_dirname, best_match)
    except Exception:
        pass

    # Strategy 3: Glob matching for similar extensions
    try:
        ext = os.path.splitext(original_filename)[1]
        if ext:
            pattern = f"**/*{ext}"
            matches = glob.glob(pattern, recursive=True)
            if matches:
                matches.sort(key=lambda m: SequenceMatcher(None, os.path.basename(m), original_filename).ratio(), reverse=True)
                best_match = matches[0]
                if SequenceMatcher(None, os.path.basename(best_match), original_filename).ratio() > 0.5:
                    return best_match
    except Exception:
        pass

    return None


def pair_header_source_files(file_list):
    # Create a dictionary to store bases and their corresponding files
    base_to_files = {}

    # Process each file in the list
    for file in file_list:
        # Extract just the filename without path
        file_name = file.split('/')[-1].split('\\')[-1]

        # Get the base name (without extension)
        base = file_name.rsplit('.', 1)[0]

        # Add to the dictionary
        if base not in base_to_files:
            base_to_files[base] = []
        base_to_files[base].append(file)

    # Create the paired list
    paired_list = []
    for base, files in base_to_files.items():
        paired_list.append(files)

    return paired_list


def get_file_contents(file_list, file_alias=None):
    """
    Reads the contents of a list of files. If a file doesn't exist, it attempts to find a similar file.
    Ensures that the content of any single physical file is included only once.
    """
    file_contents = {}
    processed_canonical_paths = set()

    for original_path_in_list in file_list:
        actual_file_to_read = None

        if os.path.exists(original_path_in_list) and os.path.isfile(original_path_in_list):
            actual_file_to_read = original_path_in_list
        else:
            similar_file = find_similar_file(original_path_in_list)
            if similar_file:
                logger.warning(f"\nFound similar file: {similar_file} instead of {original_path_in_list}")
                actual_file_to_read = similar_file

        if actual_file_to_read:
            try:
                canonical_path = os.path.abspath(actual_file_to_read)

                if canonical_path in processed_canonical_paths:
                    logger.info(f"Skipping file {original_path_in_list} as its content (from {actual_file_to_read}) has already been processed.")
                    continue

                with open(actual_file_to_read, "r", encoding='utf-8') as f:
                    file_contents[original_path_in_list] = f.read()
                processed_canonical_paths.add(canonical_path)

            except Exception as e:
                logger.error(f"Error reading file {actual_file_to_read} (originally requested as {original_path_in_list}): {str(e)}")
        else:
            logger.error(f"Error reading file {original_path_in_list}: File not found and no similar file could be determined.")

    formatted_content = ""
    for path, content in file_contents.items():
        if file_alias:
            formatted_content += f"\n\n--- BEGIN SUMMARY FOR FILE: {file_alias} ---\n{content}\n--- END SUMMARY FOR FILE: {file_alias} ---\n"
        else:
            formatted_content += f"\n\n--- BEGIN FILE: {path} ---\n{content}\n--- END FILE: {path} ---\n"

    return formatted_content


def cutoff_string(input_string, cutoff_before_match, cutoff_after_match) -> str:
    """
    Removes all text up to and including the first occurrence of cutoff_before_match,
    and all text from the last occurrence of cutoff_after_match onwards.
    Returns the text between these cutoffs, stripped of leading/trailing whitespace.
    """
    if not input_string or input_string == "":
        return ""

    # Find the start index after the first occurrence of cutoff_before_match
    before_index = input_string.find(cutoff_before_match)
    if before_index != -1:
        start = before_index + len(cutoff_before_match)
    else:
        start = 0  # No cutoff_before found, start from beginning

    # Find the last occurrence of cutoff_after_match after start
    after_index = input_string.rfind(cutoff_after_match)
    if after_index != -1 and after_index >= start:
        end = after_index
    else:
        end = len(input_string)  # No cutoff_after found, take remaining text

    # Extract and return the desired portion
    return input_string[start:end].strip()

def write_string_to_file(filename: str, content: str, append: bool = False):
    """
    Writes a given string to a file, correctly interpreting '\n' as line breaks.

    :param filename: The name of the file to write to.
    :param content: The string content to write, including line breaks.
    :param append: Append the string to the end of the file
    """
    content = content.replace("\\n", "\n").replace("\\\"", "\"")
    mode = 'a' if append else 'w'
    with open(filename, mode, encoding='utf-8') as file:
        logger.info(f"Writing {filename}")
        file.write(content)


def get_env_path() -> str:
    """
    Get the path to the .env file in the jrdev installation directory.
    
    Returns:
        Path to the .env file
    """
    storage_dir = get_persistent_storage_path()
    return os.path.join(storage_dir, '.env')

def add_to_gitignore(gitignore_path: str, ignore_str: str, create_if_dne: bool = False) -> bool:
    """
    Append a pattern to a .gitignore file. Creates the file if it doesn't exist.

    Args:
        gitignore_path: The path to the .gitignore file
        ignore_str: The pattern to add to the .gitignore file

    Returns:
        True if the pattern was added successfully, False otherwise
    """
    try:
        # Make sure the pattern is properly formatted
        ignore_pattern = ignore_str.strip()

        # Check if the file exists
        if os.path.exists(gitignore_path):
            # Read existing contents to check if the pattern already exists
            with open(gitignore_path, 'r') as f:
                lines = f.read().splitlines()

            # Check if pattern already exists
            if ignore_pattern in lines:
                return True

            # Add a newline at the end if needed
            needs_newline = lines and lines[-1] != ""

            # Append the pattern to the file
            with open(gitignore_path, 'a') as f:
                if needs_newline:
                    f.write("\n")
                f.write(f"{ignore_pattern}\n")

            logger.info(f"Added '{ignore_pattern}' to {gitignore_path}")
        elif create_if_dne:
            # File doesn't exist, create it with the pattern
            with open(gitignore_path, 'w') as f:
                f.write(f"{ignore_pattern}\n")

            logger.info(f"Created {gitignore_path} with pattern '{ignore_pattern}'")

        return True

    except Exception as e:
        logger.error(f"Error adding to gitignore: {str(e)}")
        return False


def get_persistent_storage_path() -> Path:
    """
    Returns the path to the persistent input history file (~/.jrdev),
    using os.path.expanduser to ensure cross-platform compatibility.
    Creates the directory if it doesn't exist.
    """
    path = Path.home() / ".jrdev"
    # Ensure directory exists
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def read_json_file(file_path: str) -> Optional[Union[Dict[str, Any], list]]:
    """
    Reads and parses a JSON file, returning its content.

    Args:
        file_path: The path to the JSON file.

    Returns:
        The parsed JSON data as a dictionary or list, or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"JSON file not found at {file_path}. This may be expected if it's being created for the first time.")
        return None
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from {file_path}. The file might be corrupted.")
        return None
    except IOError as e:
        logger.error(f"An I/O error occurred while reading {file_path}: {e}")
        return None


def write_json_file(file_path: str, data: Union[Dict[str, Any], list]) -> bool:
    """
    Writes Python data (dict or list) to a file in JSON format.

    Args:
        file_path: The path to the destination JSON file.
        data: The dictionary or list to write.

    Returns:
        True if the write operation was successful, False otherwise.
    """
    try:
        # Ensure the directory for the file exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except TypeError as e:
        logger.error(f"Data provided for {file_path} is not JSON serializable: {e}")
        return False
    except IOError as e:
        logger.error(f"An I/O error occurred while writing to {file_path}: {e}")
        return False


# ------------------- MIGRATION UTILITY FUNCTIONS -------------------

def move_or_copy_file(src, dst, overwrite=False):
    """
    Move a file from src to dst. If overwrite is False and dst exists, skip.
    If move fails (e.g., cross-device), fall back to copy+remove.
    Returns True if moved/copied, False if skipped, raises on error.
    """
    try:
        if os.path.exists(dst):
            if not overwrite:
                logger.info(f"File {dst} already exists, skipping.")
                return False
            else:
                logger.info(f"Overwriting {dst}")
                os.remove(dst)
        try:
            shutil.move(src, dst)
        except Exception as e:
            logger.warning(f"shutil.move failed ({e}), trying copy+remove.")
            shutil.copy2(src, dst)
            os.remove(src)
        return True
    except Exception as e:
        logger.error(f"Failed to move/copy file {src} to {dst}: {e}")
        raise

def move_or_copy_dir(src, dst, merge=False, overwrite_files=List[str]) -> bool:
    """
    Move a directory from src to dst. If overwrite is False and dst exists, skip.
    If merge is True and dst exists as a directory, merge contents recursively.
    If move fails, fall back to copytree+remove.
    Returns True if moved/copied/merged, False if skipped, raises on error.
    """
    try:
        if os.path.exists(dst):
            if os.path.isdir(dst) and merge:
                # Merge directories recursively
                logger.info(f"Merging directory {src} into existing {dst}")
                for item in os.listdir(src):
                    overwrite = item in overwrite_files
                    src_item = os.path.join(src, item)
                    dst_item = os.path.join(dst, item)
                    if os.path.isdir(src_item):
                        move_or_copy_dir(src_item, dst_item, overwrite=overwrite, merge=merge)
                    else:
                        move_or_copy_file(src_item, dst_item, overwrite=overwrite)
                # Remove source directory after merging
                shutil.rmtree(src)
                return True
            else:
                logger.info(f"Directory {dst} already exists, skipping.")
                return False
        try:
            shutil.move(src, dst)
        except Exception as e:
            logger.warning(f"shutil.move failed ({e}), trying copytree+remove.")
            shutil.copytree(src, dst)
            shutil.rmtree(src)
        return True
    except Exception as e:
        logger.error(f"Failed to move/copy directory {src} to {dst}: {e}")
        raise

def migrate_jrdev_directory(old_dir, new_dir):
    """
    Migrate all files and subdirectories from old_dir to new_dir.
    Merges directories if they already exist at the destination.
    Deletes the old directory after successful migration.
    Returns a dict: {migrated: [...], skipped: [...], errors: [...]}.
    """
    overwrite_files = {"file_index.json", "git_config.json", "jrdev_conventions.md", "jrdev_overview.md",
                       "model_profiles.json"}
    migrated = []
    skipped = []
    errors = []
    if not os.path.isdir(old_dir):
        return {"migrated": [], "skipped": [], "errors": [f"Old directory {old_dir} does not exist."]}
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
    for item in os.listdir(old_dir):
        src_path = os.path.join(old_dir, item)
        dst_path = os.path.join(new_dir, item)
        try:
            if os.path.isdir(src_path):
                result = move_or_copy_dir(src_path, dst_path, merge=True, overwrite_files=overwrite_files)
                if result:
                    migrated.append(item)
                else:
                    skipped.append(item)
            elif os.path.isfile(src_path):
                file_name = os.path.basename(src_path)
                overwrite = file_name in overwrite_files
                result = move_or_copy_file(src_path, dst_path, overwrite=overwrite)
                if result:
                    migrated.append(item)
                else:
                    skipped.append(item)
            else:
                skipped.append(item)
        except Exception as e:
            logger.error(f"Error migrating {src_path} to {dst_path}: {e}")
            errors.append(f"{item}: {e}")
    
    # Delete the old directory if migration was successful (no errors and something was migrated)
    if not errors and (migrated or not os.listdir(old_dir)):
        try:
            shutil.rmtree(old_dir)
            logger.info(f"Successfully removed old directory: {old_dir}")
        except Exception as e:
            logger.error(f"Failed to remove old directory {old_dir}: {e}")
            errors.append(f"Failed to remove old directory: {e}")
    
    return {"migrated": migrated, "skipped": skipped, "errors": errors}
