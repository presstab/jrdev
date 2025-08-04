"""
Main entry point for the jrdev package.

This script launches the Textual User Interface (TUI) by default when
the package is executed as a module using `python -m jrdev`.
"""

from jrdev.ui.tui.textual_ui import run_textual_ui


def main():
    """Launches the JrDev Textual UI."""
    run_textual_ui()


if __name__ == "__main__":
    main()
