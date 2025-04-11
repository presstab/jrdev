import os
from pathlib import Path
from typing import Iterable

from rich.style import Style
from rich.text import Text

from textual.widgets import DirectoryTree
from textual.widgets._directory_tree import DirEntry
from textual.widgets._tree import TreeNode


class FilteredDirectoryTree(DirectoryTree):
    def __init__(self, path, state):
        super().__init__(path)
        self.indexed_paths = []
        self.state = state

    """Filter out jrdev directory"""
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not (path.name.startswith("jrdev") and not path.parent.name.startswith("src"))]

    def update_indexed_paths(self):
        indexed_paths = self.state.context_manager.get_file_paths()
        if indexed_paths:
            self.indexed_paths = indexed_paths

    def render_label(self, node: TreeNode[DirEntry], base_style: Style, style: Style) -> Text:
        label = super().render_label(node, base_style, style)
        root_path = self.PATH(self.path)
        try:
            sub_paths = []
            if node.data and node.data.path:
                # climb the tree to create relative path
                n = node
                while n:
                    sub_paths.insert(0, n.data.path.name)
                    n = n.parent
                relative_path = node.data.path.name
                if sub_paths:
                    relative_path = f"{os.path.join(*sub_paths)}"

                # add styling for indexed files
                if relative_path in self.indexed_paths:
                    label.stylize("italic green")
        except ValueError:
            pass
        return label