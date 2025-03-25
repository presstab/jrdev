"""
Utility functions for working with language modules.
"""
import os
from typing import Dict, Optional

from jrdev.languages import LANGUAGE_REGISTRY


def detect_language_for_file(filepath: str) -> Optional[str]:
    """
    Detect the language type for a given file path based on its extension.

    Args:
        filepath: Path to the file

    Returns:
        String identifier of the language, or None if not recognized
    """
    ext = os.path.splitext(filepath)[1].lower()

    for lang_ext, lang_class in LANGUAGE_REGISTRY.items():
        if ext == lang_ext:
            return lang_class().language_name

    return None


def get_all_supported_extensions() -> Dict[str, str]:
    """
    Get a dictionary of all supported file extensions and their associated language names.

    Returns:
        Dictionary mapping file extensions to language names
    """
    return {ext: cls().language_name for ext, cls in LANGUAGE_REGISTRY.items()}


def detect_language(filepath):
    """
    Detect the programming language based on file extension.

    Args:
        filepath: Path to the file

    Returns:
        str: Language identifier ('cpp', 'python', 'typescript', etc.)

    Note:
        For implementation simplicity, JavaScript files are treated as 'typescript'
        since the same parser handles both languages.
    """
    ext = os.path.splitext(filepath)[1].lower()

    # Map file extensions to language identifiers
    lang_map = {
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.c++': 'cpp',
        '.hpp': 'cpp',
        '.h': 'cpp',
        '.py': 'python',
        '.js': 'typescript',  # Use TypeScript parser for JavaScript
        '.jsx': 'typescript',  # React JSX also uses TypeScript parser
        '.ts': 'typescript',
        '.tsx': 'typescript',  # TypeScript React
        '.go': 'go',
        '.java': 'java',
        '.kt': 'kotlin',
        '.kts': 'kotlin',     # Kotlin script files
        '.rb': 'ruby',
        '.rs': 'rust',
        '.swift': 'swift',
        '.php': 'php',
        '.cs': 'csharp',
    }

    # Return the language or None if not recognized
    return lang_map.get(ext)

def is_headers_language(language):
    if language == "cpp":
        return True
    return False
