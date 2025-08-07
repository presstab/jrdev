import os
import tempfile
import unittest
from unittest.mock import patch, mock_open

from jrdev.file_operations.file_utils import (
    add_to_gitignore,
    cutoff_string,
    pair_header_source_files,
)


class TestFileUtils(unittest.TestCase):
    def test_cutoff_string(self):
        self.assertEqual(
            cutoff_string("<a><b></c>", "<a>", "</c>"),
            "<b>"
        )
        self.assertEqual(
            cutoff_string("<a><b><c>", "<d>", "<c>"),
            "<a><b>"
        )
        self.assertEqual(
            cutoff_string("<a><b><c>", "<a>", "<d>"),
            "<b><c>"
        )
        self.assertEqual(
            cutoff_string("<a><b><c>", "<d>", "</d>"),
            "<a><b><c>"
        )
        self.assertEqual(
            cutoff_string("", "<a>", "<b>"),
            ""
        )
        self.assertEqual(
            cutoff_string("<a><b>", "<a>", "<b>"),
            ""
        )

    def test_pair_header_source_files(self):
        file_list = [
            "src/main.cpp",
            "src/main.h",
            "src/utils.cpp",
            "src/utils.h",
            "src/other.txt",
        ]
        paired_list = pair_header_source_files(file_list)
        self.assertIn(["src/main.cpp", "src/main.h"], paired_list)
        self.assertIn(["src/utils.cpp", "src/utils.h"], paired_list)
        self.assertIn(["src/other.txt"], paired_list)

    def test_add_to_gitignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore_path = os.path.join(tmpdir, ".gitignore")

            # Test creating a new file
            self.assertTrue(add_to_gitignore(gitignore_path, "*.log", create_if_dne=True))
            with open(gitignore_path, "r") as f:
                self.assertEqual(f.read(), "*.log\n")

            # Test adding a new pattern to an existing file
            self.assertTrue(add_to_gitignore(gitignore_path, "*.tmp"))
            with open(gitignore_path, "r") as f:
                self.assertEqual(f.read(), "*.log\n*.tmp\n")

            # Test adding a pattern that already exists
            self.assertTrue(add_to_gitignore(gitignore_path, "*.log"))
            with open(gitignore_path, "r") as f:
                self.assertEqual(f.read(), "*.log\n*.tmp\n")
