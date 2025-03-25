"""
JrDev language modules for parsing various programming languages.
"""

from jrdev.languages.cpp_lang import CppLang
from jrdev.languages.go_lang import GoLang
from jrdev.languages.java_lang import JavaLang
from jrdev.languages.kotlin_lang import KotlinLang
from jrdev.languages.lang_base import Lang
from jrdev.languages.python_lang import PythonLang
from jrdev.languages.typescript_lang import TypeScriptLang

# Registry of language handlers by file extension
LANGUAGE_REGISTRY = {
    # C++
    '.cpp': CppLang,
    '.cc': CppLang,
    '.cxx': CppLang,
    '.c++': CppLang,
    '.hpp': CppLang,
    '.h': CppLang,

    # Python
    '.py': PythonLang,

    # TypeScript/JavaScript
    '.ts': TypeScriptLang,
    '.tsx': TypeScriptLang,
    '.js': TypeScriptLang,
    '.jsx': TypeScriptLang,

    # Go
    '.go': GoLang,

    # Java
    '.java': JavaLang,

    # Kotlin
    '.kt': KotlinLang,
    '.kts': KotlinLang,
}

def get_language_for_file(filepath):
    """
    Get the appropriate language handler instance for a given file path.

    Args:
        filepath: Path to the file

    Returns:
        Lang instance for the given file type, or None if not supported
    """
    import os
    ext = os.path.splitext(filepath)[1].lower()

    if ext in LANGUAGE_REGISTRY:
        return LANGUAGE_REGISTRY[ext]()

    return None
