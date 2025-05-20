"""
JrDev Terminal package.
"""

import os

def _get_version():
    # Construct the path to the VERSION file.
    # __file__ is the path to this __init__.py file (e.g., /path/to/project/src/jrdev/__init__.py)
    # os.path.dirname(__file__) is the directory of this file (e.g., /path/to/project/src/jrdev)
    # This path navigates two levels up from src/jrdev to the project root, then to 'VERSION'.
    try:
        current_file_path = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file_path)
        # Path relative to current file: ../../VERSION
        # (src/jrdev/__init__.py -> src/jrdev -> src -> project_root -> project_root/VERSION)
        version_file_path = os.path.join(current_dir, "..", "..", "VERSION")
        version_file_path = os.path.abspath(version_file_path)
        
        with open(version_file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback if VERSION file is not found. This might occur if the package is run
        # in an environment where the relative path to VERSION is not valid (e.g., after
        # installation, if VERSION is not packaged and placed appropriately relative to
        # site-packages/jrdev/__init__.py), or if __file__ is not set as expected.
        # The task implies reading from project_root/VERSION.
        return "0.0.0+unknown"  # PEP 440 compliant for unknown version
    except Exception:
        # Catch any other unforeseen errors during version reading
        return "0.0.0+error" # Fallback for other errors

__version__ = _get_version()
