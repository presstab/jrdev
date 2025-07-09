import json
import os
import logging
from typing import Dict

from jrdev.file_operations.file_utils import JRDEV_DIR, get_persistent_storage_path
from jrdev.ui.ui import PrintType, printtype_to_string

logger = logging.getLogger("jrdev")

class TerminalTextStyles:
    """Manages loading, saving, and applying terminal text styles."""

    def __init__(self, stylesheet_path: str = None):
        """
        Initializes the style manager.

        Args:
            stylesheet_path: Optional path to the stylesheet. Defaults to
                             a file in the JRDEV_DIR.
        """
        storage_dir = get_persistent_storage_path()
        if stylesheet_path is None:
            self.stylesheet_path = os.path.join(storage_dir, "terminal_styles.json")
        else:
            self.stylesheet_path = stylesheet_path
        
        self.styles: Dict[str, str] = self._get_default_styles()
        self.load_styles()

    def _get_default_styles(self) -> Dict[str, str]:
        """Returns the default styles for each PrintType as a dictionary."""
        return {
            printtype_to_string(PrintType.INFO): "white",
            printtype_to_string(PrintType.ERROR): "bold red",
            printtype_to_string(PrintType.PROCESSING): "italic cyan",
            printtype_to_string(PrintType.LLM): "green",
            printtype_to_string(PrintType.USER): "bold yellow",
            printtype_to_string(PrintType.SUCCESS): "bold green",
            printtype_to_string(PrintType.WARNING): "bold yellow",
            printtype_to_string(PrintType.COMMAND): "bold blue",
            printtype_to_string(PrintType.HEADER): "bold underline white",
            printtype_to_string(PrintType.SUBHEADER): "bold white",
        }

    def load_styles(self) -> None:
        """Loads styles from the stylesheet file, merging them with defaults."""
        if os.path.exists(self.stylesheet_path):
            try:
                with open(self.stylesheet_path, 'r', encoding='utf-8') as f:
                    user_styles = json.load(f)
                # Merge user styles into default styles, overwriting defaults
                self.styles.update(user_styles)
                logger.info(f"Loaded terminal styles from {self.stylesheet_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading terminal styles from {self.stylesheet_path}: {e}. Using default styles.")
        else:
            logger.info("Terminal stylesheet not found. Using default styles and creating a new one.")
            self.save_styles()

    def save_styles(self) -> bool:
        """Saves the current styles to the stylesheet file."""
        try:
            os.makedirs(os.path.dirname(self.stylesheet_path), exist_ok=True)
            with open(self.stylesheet_path, 'w', encoding='utf-8') as f:
                json.dump(self.styles, f, indent=4, sort_keys=True)
            logger.info(f"Saved terminal styles to {self.stylesheet_path}")
            return True
        except IOError as e:
            logger.error(f"Error saving terminal styles to {self.stylesheet_path}: {e}")
            return False

    def get_style(self, print_type: PrintType) -> str:
        """Gets the style string for a given PrintType."""
        key = printtype_to_string(print_type)
        # Default to plain white if a style is somehow missing
        return self.styles.get(key, "white")

    def set_style(self, print_type: PrintType, style_str: str) -> None:
        """Sets the style for a given PrintType."""
        key = printtype_to_string(print_type)
        self.styles[key] = style_str
