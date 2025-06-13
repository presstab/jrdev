import re

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
    normalized_snippet = code_snippet.replace('\r\n', '\n').replace('\\n', '\n').replace('\\"', '"')
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
            if snippet_line.strip() != line.strip() and snippet_line.strip() not in line:
                found = False
                break
        if found:
            return i, i + len(snippet_lines)

    return -1, -1

def contains_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def is_valid_url(url: str) -> bool:
    """
    Returns True if the string is a well-formed HTTP or HTTPS URL, False otherwise.
    Accepts only http:// or https:// schemes, requires a valid domain or IP, and optional port/path/query/fragment.
    """
    # Basic check for http(s) scheme and netloc
    pattern = re.compile(
        r'^(https?://)'                  # http:// or https://
        r'([\w\-\.]+)'                # domain or subdomain
        r'(\:[0-9]{1,5})?'              # optional port
        r'(/[\w\-\./%]*)?'            # optional path
        r'(\?[\w\-\./%&=;:+@]*)?'    # optional query
        r'(#[\w\-\./%&=;:+@]*)?'      # optional fragment
        r'$',
        re.IGNORECASE
    )
    if not isinstance(url, str):
        return False
    if len(url) > 2048:
        return False
    if not pattern.match(url):
        return False
    # Further check: must not contain spaces or illegal chars
    if ' ' in url or '\n' in url or '\r' in url:
        return False
    return True

# -------------------
# Validation helpers
# -------------------
def is_valid_name(name: str, min_len: int = 1, max_len: int = 64) -> bool:
    """
    Validates provider/model names: alphanumeric, underscores, hyphens; no path separators or control chars.
    """
    if not isinstance(name, str):
        return False
    if not (min_len <= len(name) <= max_len):
        return False
    # Disallow path separators and control chars
    if any(c in name for c in ('\\', '\0', '\n', '\r', '\t')):
        return False
    # Only allow alphanumeric, underscore, hyphen
    if not re.fullmatch(r'[A-Za-z0-9_:/.\-]+', name):
        return False
    return True

def is_valid_env_key(env_key: str, min_len: int = 1, max_len: int = 128) -> bool:
    """
    Validates env_key: alphanumeric, underscores, hyphens, uppercase; no path separators or control chars.
    """
    if not isinstance(env_key, str):
        return False
    if not (min_len <= len(env_key) <= max_len):
        return False
    if any(c in env_key for c in ('/', '\\', '\0', '\n', '\r', '\t')):
        return False
    # Only allow alphanumeric, underscore, hyphen (env keys are often uppercase)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', env_key):
        return False
    return True

def is_valid_cost(value: float, min_value: float = 0.0, max_value: float = 1000.0) -> bool:
    """
    Validates cost values: float between 0 and 1000 (inclusive).
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if not (min_value <= v <= max_value):
        return False
    return True

def is_valid_context_window(value: int, min_value: int = 1, max_value: int = 1_000_000_000) -> bool:
    """
    Validates context window: integer between 1 and 1,000,000,000 (inclusive).
    """
    try:
        v = int(value)
    except (TypeError, ValueError):
        return False
    if not (min_value <= v <= max_value):
        return False
    return True
