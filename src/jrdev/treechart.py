#!/usr/bin/env python3

"""
Tree chart utility for generating file structure diagrams.
"""

import os
import sys
from pathlib import Path


def generate_compact_tree(directory=None, output_file=None, max_depth=None,
                        exclude_dirs=None, exclude_files=None, include_files=None):
    """
    Generate a more token-efficient representation of the directory structure.

    Args:
        directory: Root directory to start from. Defaults to current directory.
        output_file: If provided, write output to this file.
        max_depth: Maximum depth to traverse.
        exclude_dirs: List of directory names to exclude.
        exclude_files: List of filename patterns to exclude.
        include_files: List of filename patterns to include (overrides exclude_files).

    Returns:
        String representation of the directory tree.
    """
    if directory is None:
        directory = os.getcwd()
    
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', '.venv', 'venv', 'node_modules', '.idea', '.vscode']
    
    if exclude_files is None:
        exclude_files = ['*.pyc', '*.pyo', '*~', '.DS_Store', 'Thumbs.db']
    
    # Convert to Path object
    directory_path = Path(directory)
    base_dir = directory_path.name
    
    # Structure to hold paths in a nested dictionary
    file_dict = {}
    
    def should_exclude_dir(dir_name):
        """Check if directory should be excluded."""
        return dir_name.startswith('.') or dir_name in exclude_dirs
    
    def should_exclude_file(file_name):
        """Check if file should be excluded."""
        if include_files is not None:
            # If include_files is specified, only include these files
            for pattern in include_files:
                if Path(file_name).match(pattern):
                    return False
            return True
        
        # Exclude files based on exclude_files patterns
        if file_name.startswith('.'):
            return True
        
        for pattern in exclude_files:
            if Path(file_name).match(pattern):
                return True
        
        return False
    
    def collect_files(current_path, path_parts=None, depth=0):
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
                
                if entry_path.is_dir() and not should_exclude_dir(entry):
                    # Recursively process subdirectory
                    new_path_parts = path_parts + [entry]
                    collect_files(entry_path, new_path_parts, depth + 1)
                    
                elif entry_path.is_file() and not should_exclude_file(entry):
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
    lines = [f"ROOT={base_dir}"]
    
    def format_dict(d, prefix=""):
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


def generate_tree(directory=None, output_file=None, max_depth=None,
                  exclude_dirs=None, exclude_files=None, include_files=None):
    """
    Generate a tree representation of the directory structure.

    Args:
        directory: Root directory to start from. Defaults to current directory.
        output_file: If provided, write output to this file.
        max_depth: Maximum depth to traverse.
        exclude_dirs: List of directory names to exclude.
        exclude_files: List of filename patterns to exclude.
        include_files: List of filename patterns to include (overrides exclude_files).

    Returns:
        String representation of the directory tree.
    """
    if directory is None:
        directory = os.getcwd()
    
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', '.venv', 'venv', 'node_modules', '.idea', '.vscode']
    
    if exclude_files is None:
        exclude_files = ['*.pyc', '*.pyo', '*~', '.DS_Store', 'Thumbs.db']
    
    # Convert to Path object
    directory_path = Path(directory)
    
    # Get the top-level directory name
    result = [f"Directory structure of: {directory_path}\n"]
    
    def should_exclude_dir(dir_name):
        """Check if directory should be excluded."""
        return dir_name.startswith('.') or dir_name in exclude_dirs
    
    def should_exclude_file(file_name):
        """Check if file should be excluded."""
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
        
        return False
    
    def walk_directory(path, prefix="", depth=0):
        """Recursively walk the directory tree."""
        if max_depth is not None and depth > max_depth:
            return
        
        dirs = []
        files = []
        
        # Sort entries for consistent output
        for entry in sorted(os.listdir(path)):
            entry_path = path / entry
            if entry_path.is_dir() and not should_exclude_dir(entry):
                dirs.append(entry)
            elif entry_path.is_file() and not should_exclude_file(entry):
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


def main():
    """Command-line interface for the tree chart utility."""
    directory = os.getcwd()
    
    # Generate tree and print to stdout
    tree_output = generate_tree(directory)
    print(tree_output)


if __name__ == "__main__":
    main()