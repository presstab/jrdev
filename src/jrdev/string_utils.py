

def find_code_snippet(lines, code_snippet):
    """
    Find a code snippet in file lines.

    Args:
        lines: List of file lines
        code_snippet: Exact code snippet to find

    Returns:
        tuple: (start_idx, end_idx) of the snippet, or (-1, -1) if not found
    """
    # Normalize line endings in the snippet
    normalized_snippet = code_snippet.replace('\r\n', '\n').rstrip('\n')
    snippet_lines = normalized_snippet.split('\n')

    # If the snippet is empty, return not found
    if not snippet_lines:
        return -1, -1

    # If the snippet is a single line, do a simple search
    if len(snippet_lines) == 1:
        for i, line in enumerate(lines):
            if snippet_lines[0] in line:
                return i, i + 1
        return -1, -1

    # For multi-line snippets, do a sliding window search
    for i in range(len(lines) - len(snippet_lines) + 1):
        found = True
        for j, snippet_line in enumerate(snippet_lines):
            line = lines[i + j].rstrip('\n')  # Remove trailing newline for comparison
            # Strip whitespace for comparison to handle indentation differences
            if snippet_line.strip() != line.strip() and snippet_line not in line:
                found = False
                break
        if found:
            return i, i + len(snippet_lines)

    return -1, -1