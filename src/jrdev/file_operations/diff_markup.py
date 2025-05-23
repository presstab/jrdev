import re
import logging
from typing import Any, Dict, List

logger = logging.getLogger("jrdev")

def apply_diff_markup(original_content: str, diff: List[str]) -> List[str]:
    full_content_lines = original_content.splitlines()  # These lines do NOT have \n

    diff_markers: Dict[int, Any] = {}  # Stores "delete" or ("replace", new_text_stripped)
    insertions: Dict[int, List[str]] = {}  # Stores {line_idx: ["+stripped_content", ...]}
    hunk_start = None

    logger.info(f"Processing diff with {len(diff)} lines")

    current_line_idx_in_diff = 0
    hunk_data = []

    while current_line_idx_in_diff < len(diff):
        line_from_diff = diff[current_line_idx_in_diff]

        if line_from_diff.startswith('---') or line_from_diff.startswith('+++') or line_from_diff.startswith('diff'):
            current_line_idx_in_diff += 1
            continue

        if line_from_diff.startswith('@@'):
            match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line_from_diff)
            if match:
                old_start, old_count, new_start, new_count = map(int, match.groups())
                hunk_start_original_idx = old_start - 1

                current_hunk = {
                    'start': hunk_start_original_idx,
                    'old_count': old_count,
                    'lines': []
                }

                current_line_idx_in_diff += 1
                while current_line_idx_in_diff < len(diff) and not diff[current_line_idx_in_diff].startswith('@@'):
                    current_hunk['lines'].append(diff[current_line_idx_in_diff])
                    current_line_idx_in_diff += 1

                hunk_data.append(current_hunk)
                continue
            else:
                current_line_idx_in_diff += 1
                continue
        current_line_idx_in_diff += 1

    for hunk in hunk_data:
        hunk_original_start_idx = hunk['start']
        current_original_offset = 0  # Offset within the original lines this hunk refers to

        for diff_op_line in hunk['lines']:  # e.g., "-old line\n", "+new line\n", " context\n"
            if diff_op_line.startswith('-'):
                # This deletion applies to original line: hunk_original_start_idx + current_original_offset
                position_in_original = hunk_original_start_idx + current_original_offset
                diff_markers[position_in_original] = "delete"
                current_original_offset += 1
            elif diff_op_line.startswith('+'):
                # This addition is inserted *before* original line: hunk_original_start_idx + current_original_offset
                # Or, if it follows a delete at the same position, it's part of a replace.
                position_in_original_for_insertion = hunk_original_start_idx + current_original_offset

                # THE KEY FIX: Strip trailing whitespace (including \n, \r\n) from the content
                content_to_add_or_replace = diff_op_line[1:].rstrip()

                if diff_markers.get(position_in_original_for_insertion) == "delete":
                    # This is a replacement for the line we just marked as "delete"
                    diff_markers[position_in_original_for_insertion] = ("replace", content_to_add_or_replace)
                else:
                    # This is a pure addition
                    if position_in_original_for_insertion not in insertions:
                        insertions[position_in_original_for_insertion] = []
                    insertions[position_in_original_for_insertion].append("+" + content_to_add_or_replace)
                # Note: Additions do not increment current_original_offset because they don't consume an original line
            elif diff_op_line.startswith(' ') or diff_op_line == ' ':  # Context line
                current_original_offset += 1
            elif diff_op_line == '' or diff_op_line.startswith('\\'):  # Empty line in diff or "\ No newline..."
                pass  # Context lines handle their own offset. No-newline doesn't affect offset.
            else:  # Should not happen in a well-formed diff hunk line
                current_original_offset += 1

    # Consolidate consecutive insertions
    insertions_combined = {}
    current_insertion_start_idx = None
    current_insertion_group = []
    prev_insertion_line_num = -2  # Initialize to a value that won't match 0

    for line_num in sorted(insertions.keys()):
        if current_insertion_start_idx is None:
            current_insertion_start_idx = line_num
            current_insertion_group = insertions[line_num].copy()
            prev_insertion_line_num = line_num
        elif line_num == prev_insertion_line_num:  # Multiple insertions before the SAME original line
            current_insertion_group.extend(insertions[line_num])
            # prev_insertion_line_num remains the same
        elif line_num == prev_insertion_line_num + 1 and False:  # This logic for consecutive lines was complex;
            # insertions are keyed by the original line they precede.
            # Simpler: group all insertions for the *same* original line index.
            pass  # The original grouping logic might need review if complex multi-line insertions are not grouped as expected.
            # For now, the current logic groups insertions that occur *before the same original line index*.
        else:  # New insertion point
            if current_insertion_start_idx is not None:  # Ensure group is not empty
                insertions_combined[current_insertion_start_idx] = current_insertion_group
            current_insertion_start_idx = line_num
            current_insertion_group = insertions[line_num].copy()
            prev_insertion_line_num = line_num

    if current_insertion_start_idx is not None:
        insertions_combined[current_insertion_start_idx] = current_insertion_group

    marked_content = []
    for idx, original_line_content in enumerate(full_content_lines):  # original_line_content has no \n

        if idx in insertions_combined:
            for line_to_insert in insertions_combined[idx]:  # line_to_insert is "+stripped_content"
                marked_content.append(line_to_insert)

        if idx in diff_markers:
            marker_action = diff_markers[idx]
            if marker_action == "delete":
                marked_content.append("-" + original_line_content)
            elif isinstance(marker_action, tuple) and marker_action[0] == "replace":
                new_text_stripped = marker_action[1]  # This is already stripped
                marked_content.append("-" + original_line_content)
                marked_content.append("+" + new_text_stripped)
            # else: # This case should not be hit if diff_markers only has "delete" or ("replace",...)
            #     marked_content.append(" " + original_line_content) # Fallback for safety
        else:  # Unchanged line
            marked_content.append(" " + original_line_content)

    # Handle insertions after the last line of the original file
    eof_original_idx = len(full_content_lines)
    if eof_original_idx in insertions_combined:
        for line_to_insert in insertions_combined[eof_original_idx]:
            marked_content.append(line_to_insert)

    return marked_content