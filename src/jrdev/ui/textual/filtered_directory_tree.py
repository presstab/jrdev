from pathlib import Path
from typing import Iterable

from textual.widgets import DirectoryTree


class FilteredDirectoryTree(DirectoryTree):
    """Filter out jrdev directory"""
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not (path.name.startswith("jrdev") and not path.parent.name.startswith("src"))]