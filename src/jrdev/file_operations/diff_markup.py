import re
import logging
from typing import Any, Dict, List

logger = logging.getLogger("jrdev")

def apply_diff_markup(original_content: str, diff: List[str]) -> List[str]:
    full_content_lines = original_content.splitlines()  # These lines do NOT have \n

    diff_markers: Dict[int, Any] = {}  # Stores "delete" or ("replace", new_text_stripped)
    insertions: Dict[int, List[str]] = {}  # Stores {line_idx: ["+stripped_content", ...]}

    # Part 1: Parse diff into hunks with necessary information
    parsed_hunks = []
    current_diff_line_idx = 0
    while current_diff_line_idx < len(diff):
        diff_line = diff[current_diff_line_idx]

        if diff_line.startswith('---') or diff_line.startswith('+++') or diff_line.startswith('diff '):
            current_diff_line_idx += 1
            continue

        if diff_line.startswith('@@'):
            # Guidance 1: Use regex that handles optional line counts
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', diff_line)
            if match:
                old_start_str, _old_count_str, _new_start_str, _new_count_str = match.groups()
                old_start = int(old_start_str)
                
                # Guidance 1: Calculate hunk_original_start_idx (0-based)
                # If old_start is 0 (e.g., diff against /dev/null or adding to empty file),
                # hunk_original_start_idx will be -1.
                hunk_original_start_idx = old_start - 1

                hunk_lines_content = []
                current_diff_line_idx += 1 # Move past the @@ line
                while current_diff_line_idx < len(diff) and not diff[current_diff_line_idx].startswith('@@'):
                    hunk_lines_content.append(diff[current_diff_line_idx])
                    current_diff_line_idx += 1
                
                parsed_hunks.append({
                    'hunk_original_start_idx': hunk_original_start_idx,
                    'lines': hunk_lines_content
                })
                # current_diff_line_idx is now at the start of the next hunk or EOF, so continue outer loop
                continue 
            else:
                # Malformed hunk header. For robustness, skip and continue.
                # In a stricter system, this might log an error or raise an exception.
                current_diff_line_idx += 1
                continue
        
        # If a line is not a diff header, hunk header, or part of a hunk, skip it.
        # This handles cases like index lines or other metadata if present, though
        # create_diff usually produces a clean unified diff.
        current_diff_line_idx += 1 

    # Part 2: Process each parsed hunk (Guidance 2)
    for hunk in parsed_hunks:
        hunk_original_start_idx = hunk['hunk_original_start_idx']
        current_original_offset = 0  # 0-based offset within the original lines this hunk section refers to

        for diff_op_line_raw in hunk['lines']:
            # diff_op_line_raw is a line from the diff, e.g., "-old_line\n", "+new_line\n", " context_line\n"
            
            if diff_op_line_raw.startswith('-'):
                position_in_original = hunk_original_start_idx + current_original_offset
                diff_markers[position_in_original] = "delete"
                current_original_offset += 1
            elif diff_op_line_raw.startswith('+'):
                # Guidance 2: Remove '+' prefix and trailing newlines for the content
                content_to_add = diff_op_line_raw[1:].rstrip('\r\n')
                
                # Guidance 2: Check if this addition is part of a replacement
                # A replacement occurs if a '-' line for an original line is immediately followed by a '+' line.
                # The 'current_original_offset' would have been incremented by the preceding '-' line.
                idx_of_potentially_deleted_line = hunk_original_start_idx + current_original_offset - 1
                
                if diff_markers.get(idx_of_potentially_deleted_line) == "delete":
                    diff_markers[idx_of_potentially_deleted_line] = ("replace", content_to_add)
                else:
                    # Pure addition
                    insertion_idx = hunk_original_start_idx + current_original_offset
                    # Guidance 2: Special case for insertion_idx when hunk_original_start_idx is -1
                    if hunk_original_start_idx == -1: # Indicates additions to an empty file or at the very start
                        insertion_idx = 0
                    
                    insertions.setdefault(insertion_idx, []).append("+" + content_to_add)
                # Added lines do NOT increment current_original_offset
            elif diff_op_line_raw.startswith(' '):
                # Context line
                current_original_offset += 1
            elif diff_op_line_raw.startswith('\\'): # "\ No newline at end of file"
                pass # This diff directive does not affect markup or offsets of content lines
            # Other lines (e.g., empty lines within hunk content if they occur) are ignored if they don't match known prefixes.

    # Part 3: Assemble the final marked-up content (Guidance 4)
    # Guidance 3: The `insertions_combined` step is removed by building `insertions` correctly.
    marked_content = []
    for idx, original_line_content in enumerate(full_content_lines):
        # 1. Add insertions that come *before* this original line
        if idx in insertions:
            marked_content.extend(insertions[idx])

        # 2. Process the original line itself (delete, replace, or context)
        if idx in diff_markers:
            marker_action = diff_markers[idx]
            if marker_action == "delete":
                marked_content.append("-" + original_line_content)
            elif isinstance(marker_action, tuple) and marker_action[0] == "replace":
                new_text_stripped = marker_action[1]
                marked_content.append("-" + original_line_content)
                marked_content.append("+" + new_text_stripped)
            # If marker_action was just "delete" but an insertion happened at idx (handled above),
            # this original line is still processed for its deletion marker.
        else:  # Unchanged line (not marked for deletion or replacement)
            marked_content.append(" " + original_line_content)

    # Handle insertions that occur *after* the very last line of the original file
    # This also covers the case where the original file was empty (len(full_content_lines) == 0),
    # and all lines are insertions at index 0.
    eof_insertion_idx = len(full_content_lines)
    if eof_insertion_idx in insertions:
        marked_content.extend(insertions[eof_insertion_idx])

    return marked_content

def remove_diff_markup(edited_content_list: List[str]):
    """
    Takes code that has been marked up in diff format and removes the formatting.
    Args:
        edited_content_list: diff marked up code file split into line strings.

    Returns: a single string with all diff markup removed.

    """
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

    return "\n".join(new_content_lines)
