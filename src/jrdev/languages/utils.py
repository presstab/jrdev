"""
Utility functions for working with language modules.
"""
import os
from typing import Dict, Type, Optional

from jrdev.languages.lang_base import Lang
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