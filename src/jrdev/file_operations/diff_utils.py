import re
from difflib import unified_diff
from typing import List


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

def create_diff(original_content: str, new_content: str, filepath) -> List:
    original_lines = original_content.splitlines(True)
    new_lines = new_content.splitlines(True)

    return list(unified_diff(
        original_lines,
        new_lines,
        fromfile=f'a/{filepath}',
        tofile=f'b/{filepath}',
        n=3
    ))