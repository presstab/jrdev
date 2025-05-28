#!/usr/bin/env python3

"""
Tree chart utility for generating file structure diagrams.
"""

import os
import re
import fnmatch
from pathlib import Path
from typing import List, Dict, Optional, Union, Any


def parse_gitignore(directory: str) -> List[str]:
    """
    Parse .gitignore file in the specified directory and return patterns.

    Args:
        directory: The directory containing the .gitignore file.

    Returns:
        A list of ignore patterns.
    """
    gitignore_path = os.path.join(directory, '.gitignore')
    ignore_patterns: List[str] = []

    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        # Handle negation patterns (those starting with !)
                        ignore_patterns.append(line)
        except Exception:
            # If there's an error reading the file, just continue without patterns
            pass

    return ignore_patterns


def is_ignored_by_gitignore(path: Union[str, Path], patterns: List[str], root_dir: str) -> bool:
    """
    Check if a path should be ignored based on gitignore patterns.

    Args:
        path: The path to check.
        patterns: List of gitignore patterns.
        root_dir: The root directory for relative paths.

    Returns:
        True if the path should be ignored, False otherwise.
    """
    """
       Check if a path should be ignored based on .gitignore patterns
       using fnmatch only (no manual regex).
       """
    if not patterns:
        return False

    # normalize
    rel = os.path.relpath(str(path), root_dir).replace(os.sep, '/')
    name = os.path.basename(rel)

    for pat in patterns:
        negated = pat.startswith('!')
        if negated:
            pat = pat[1:]

        # strip any leading slash for fnmatch
        if pat.startswith('/'):
            pat = pat[1:]

        # if the pattern mentions a slash, match against the full relative path
        target = rel if '/' in pat else name

        if fnmatch.fnmatch(target, pat):
            return not negated

    return False


def generate_compact_tree(
    directory: Optional[str] = None,
    output_file: Optional[str] = None,
    max_depth: Optional[int] = None,
    exclude_dirs: Optional[List[str]] = None,
    exclude_files: Optional[List[str]] = None,
    include_files: Optional[List[str]] = None,
    use_gitignore: bool = True
) -> str:
    """
    Generate a more token-efficient representation of the directory structure.

    Args:
        directory: Root directory to start from. Defaults to current directory.
        output_file: If provided, write output to this file.
        max_depth: Maximum depth to traverse.
        exclude_dirs: List of directory names to exclude.
        exclude_files: List of filename patterns to exclude.
        include_files: List of filename patterns to include (overrides exclude_files).
        use_gitignore: Whether to respect .gitignore patterns. Defaults to True.

    Returns:
        String representation of the directory tree.
    """
    if directory is None:
        directory = os.getcwd()

    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', '.venv', 'venv', 'node_modules', '.idea', '.vscode']

    if exclude_files is None:
        exclude_files = ['*.pyc', '*.pyo', '*~', '.DS_Store', 'Thumbs.db', '.env', '*.env', '*filetree.txt',
                         '*filecontext.md', '*.log', '*overview.md']

    if '.env' not in exclude_files:
        exclude_files.append('.env')

    # Convert to Path object
    directory_path = Path(directory)
    base_dir = directory_path.name

    # Parse .gitignore file if it exists and we're using it
    gitignore_patterns: List[str] = []
    if use_gitignore:
        gitignore_patterns = parse_gitignore(directory)

    # Structure to hold paths in a nested dictionary
    file_dict: Dict[str, Any] = {}

    def should_exclude_dir(dir_path: Path, dir_name: str) -> bool:
        """Check if directory should be excluded."""
        # First check built-in exclusions
        if dir_name.startswith('.') or dir_name in exclude_dirs:
            return True

        # Then check gitignore patterns
        if use_gitignore and gitignore_patterns:
            return is_ignored_by_gitignore(dir_path, gitignore_patterns, directory)

        return False

    def should_exclude_file(file_path: Path, file_name: str) -> bool:
        """Check if file should be excluded."""
        # First check include patterns if specified
        if include_files is not None:
            # If include_files is specified, only include these files
            for pattern in include_files:
                if Path(file_name).match(pattern):
                    return False
            return True

        # Then check built-in exclusions
        if file_name.startswith('.'):
            return True

        for pattern in exclude_files:
            if Path(file_name).match(pattern):
                return True

        # Finally check gitignore patterns
        if use_gitignore and gitignore_patterns:
            return is_ignored_by_gitignore(file_path, gitignore_patterns, directory)

        return False

    def collect_files(current_path: Path, path_parts: Optional[List[str]] = None, depth: int = 0) -> None:
        """Collect all files into a nested dictionary structure."""
        if max_depth is not None and depth > max_depth:
            return

        if path_parts is None:
            path_parts = []

        try:
            entries = sorted(os.listdir(current_path))
            files = []

            for entry in entries:
                entry_path = current_path / entry

                if entry_path.is_dir() and not should_exclude_dir(entry_path, entry):
                    # Recursively process subdirectory
                    new_path_parts = path_parts + [entry]
                    collect_files(entry_path, new_path_parts, depth + 1)

                elif entry_path.is_file() and not should_exclude_file(entry_path, entry):
                    # Add file to the list
                    files.append(entry)

            # If we have files at this level, add them to the dictionary
            if files:
                # Build the nested dictionary path
                current_dict = file_dict
                for part in path_parts:
                    if part not in current_dict:
                        current_dict[part] = {}
                    current_dict = current_dict[part]

                # Store files at this level
                current_dict["_files"] = files

        except (PermissionError, FileNotFoundError, OSError):
            pass

    # Start recursively collecting files
    collect_files(directory_path)

    # Generate compact JSON-like output
    lines: List[str] = [f"ROOT={base_dir}"]

    def format_dict(d: Dict[str, Any], prefix: str = "") -> None:
        """Format the nested dictionary into compact representation."""
        # Process files at this level
        if "_files" in d:
            files_str = ",".join(d["_files"])
            lines.append(f"{prefix}:[{files_str}]")

        # Process subdirectories
        for key in sorted(d.keys()):
            if key != "_files":
                new_prefix = f"{prefix}/{key}" if prefix else key
                format_dict(d[key], new_prefix)

    # Format the file dictionary
    format_dict(file_dict)

    # Join all lines and write to file if specified
    output = "\n".join(lines)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)

    return output


def generate_tree(
    directory: Optional[str] = None,
    output_file: Optional[str] = None,
    max_depth: Optional[int] = None,
    exclude_dirs: Optional[List[str]] = None,
    exclude_files: Optional[List[str]] = None,
    include_files: Optional[List[str]] = None,
    use_gitignore: bool = True
) -> str:
    """
    Generate a tree representation of the directory structure.

    Args:
        directory: Root directory to start from. Defaults to current directory.
        output_file: If provided, write output to this file.
        max_depth: Maximum depth to traverse.
        exclude_dirs: List of directory names to exclude.
        exclude_files: List of filename patterns to exclude.
        include_files: List of filename patterns to include (overrides exclude_files).
        use_gitignore: Whether to respect .gitignore patterns. Defaults to True.

    Returns:
        String representation of the directory tree.
    """
    if directory is None:
        directory = os.getcwd()

    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', '.venv', 'venv', 'node_modules', '.idea', '.vscode']

    if exclude_files is None:
        exclude_files = ['*.pyc', '*.pyo', '*~', '.DS_Store', 'Thumbs.db', '.env', '*.env', '*filetree.txt',
                         '*filecontext.md', '*.log', '*overview.md']

    if '.env' not in exclude_files:
        exclude_files.append('.env')

    # Convert to Path object
    directory_path = Path(directory)

    # Parse .gitignore file if it exists and we're using it
    gitignore_patterns: List[str] = []
    if use_gitignore:
        gitignore_patterns = parse_gitignore(directory)

    # Get the top-level directory name
    result: List[str] = [f"Directory structure of: {directory_path}\n"]

    def should_exclude_dir(dir_path: Path, dir_name: str) -> bool:
        """Check if directory should be excluded."""
        # First check built-in exclusions
        if dir_name.startswith('.') or dir_name in exclude_dirs:
            return True

        # Then check gitignore patterns
        if use_gitignore and gitignore_patterns:
            return is_ignored_by_gitignore(dir_path, gitignore_patterns, directory)

        return False

    def should_exclude_file(file_path: Path, file_name: str) -> bool:
        """Check if file should be excluded."""
        # First check include patterns if specified
        if include_files is not None:
            # If include_files is specified, only include these files
            for pattern in include_files:
                if Path(file_name).match(pattern):
                    return False
            return True

        # Otherwise exclude files based on exclude_files patterns
        if file_name.startswith('.'):
            return True

        for pattern in exclude_files:
            if Path(file_name).match(pattern):
                return True

        # Finally check gitignore patterns
        if use_gitignore and gitignore_patterns:
            return is_ignored_by_gitignore(file_path, gitignore_patterns, directory)

        return False

    def walk_directory(path: Path, prefix: str = "", depth: int = 0) -> None:
        """Recursively walk the directory tree."""
        if max_depth is not None and depth > max_depth:
            return

        dirs = []
        files = []

        # Sort entries for consistent output
        for entry in sorted(os.listdir(path)):
            entry_path = path / entry
            if entry_path.is_dir() and not should_exclude_dir(entry_path, entry):
                dirs.append(entry)
            elif entry_path.is_file() and not should_exclude_file(entry_path, entry):
                files.append(entry)

        # Process directories
        for i, dir_name in enumerate(dirs):
            if i == len(dirs) - 1 and not files:
                # Last entry, no files
                result.append(f"{prefix}└── {dir_name}/")
                walk_directory(path / dir_name, f"{prefix}    ", depth + 1)
            else:
                result.append(f"{prefix}├── {dir_name}/")
                walk_directory(path / dir_name, f"{prefix}│   ", depth + 1)

        # Process files
        for i, file_name in enumerate(files):
            if i == len(files) - 1:
                # Last entry
                result.append(f"{prefix}└── {file_name}")
            else:
                result.append(f"{prefix}├── {file_name}")

    # Start walking from the root directory with a depth of 0
    try:
        if directory_path.is_dir():
            walk_directory(directory_path)
        else:
            result.append(f"Error: {directory_path} is not a directory.")
    except PermissionError:
        result.append(f"Error: Permission denied accessing {directory_path}")
    except Exception as e:
        result.append(f"Error: {str(e)}")

    # Convert result to string
    output = "\n".join(result)

    # Write to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)

    return output


def main() -> None:
    """Command-line interface for the tree chart utility."""
    directory = os.getcwd()

    # Generate tree and print to stdout
    tree_output = generate_tree(directory)
    print(tree_output)


if __name__ == "__main__":
    main()
