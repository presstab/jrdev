import os
import sys
import unittest
import asyncio
import json
import shutil
import tempfile
from typing import Any, Dict, List, Optional, cast
from unittest.mock import patch, MagicMock, AsyncMock

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.file_utils import *


class TestFileUtils(unittest.TestCase):
    """Tests for functions in file_utils.py"""

    mock_json_path: str
    temp_dir: str
    original_file: str
    expected_file: str
    temp_file: str

    def setUp(self) -> None:
        """Set up test environment"""
        self.mock_json_path = os.path.join(os.path.dirname(__file__), "mock/insert_after_function_mock.json")
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Define paths for original and expected files
        self.original_file = os.path.join(os.path.dirname(__file__), "mock/pricechartwidget.cpp")
        self.expected_file = os.path.join(os.path.dirname(__file__), "mock/pricechartwidget_after.cpp")
        
        # Copy original file to temp directory
        self.temp_file = os.path.join(self.temp_dir, "pricechartwidget.cpp")
        shutil.copy2(self.original_file, self.temp_file)

    def tearDown(self) -> None:
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir)

    def test_apply_file_changes(self) -> None:
        """Test apply_file_changes with mock JSON data"""
        # Load the mock JSON file
        with open(self.mock_json_path, "r") as f:
            json_content = f.read()
        
        # Extract the JSON content using cutoff_string
        json_content = cutoff_string(json_content, "```json", "```")
        
        # Parse the JSON content
        changes_json = manual_json_parse(json_content)
        
        # Modify the file paths in the changes to point to our temp directory
        for change in changes_json["changes"]:
            if "filename" in change:
                original_path = change["filename"]
                filename = os.path.basename(original_path)
                change["filename"] = os.path.join(self.temp_dir, filename)
        
        # Apply the changes
        with patch('jrdev.file_utils.terminal_print') as mock_terminal_print:
            files_changed = apply_file_changes(changes_json)
        
        # Verify that the file was changed
        self.assertEqual(len(files_changed), 1)
        
        # Read the content of the changed file
        with open(files_changed[0], "r") as f:
            actual_content = f.read()
        
        # Read the expected content
        with open(self.expected_file, "r") as f:
            expected_content = f.read()
        
        # Compare the actual content with the expected content
        self.assertEqual(actual_content, expected_content)
        
    def test_python_function_insertion(self) -> None:
        """Test inserting content after a Python function"""
        # Define paths for original and expected Python files
        python_mock_path = os.path.join(os.path.dirname(__file__), "mock/insert_after_function_mock_python.json")
        python_original_file = os.path.join(os.path.dirname(__file__), "mock/price_chart_widget.py")
        python_expected_file = os.path.join(os.path.dirname(__file__), "mock/price_chart_widget_after.py")
        
        # Copy original Python file to temp directory
        python_temp_file = os.path.join(self.temp_dir, "price_chart_widget.py")
        shutil.copy2(python_original_file, python_temp_file)
        
        # Load the Python mock JSON file
        with open(python_mock_path, "r") as f:
            json_content = f.read()
        
        # Extract the JSON content using cutoff_string
        json_content = cutoff_string(json_content, "```json", "```")
        
        # Parse the JSON content
        changes_json = manual_json_parse(json_content)
        
        # Modify the file paths in the changes to point to our temp directory
        for change in changes_json["changes"]:
            if "filename" in change:
                original_path = change["filename"]
                filename = os.path.basename(original_path)
                change["filename"] = os.path.join(self.temp_dir, filename)
        
        # Apply the changes
        with patch('jrdev.file_utils.terminal_print') as mock_terminal_print:
            files_changed = apply_file_changes(changes_json)
        
        # Verify that the file was changed
        self.assertEqual(len(files_changed), 1)
        
        # Read the content of the changed file
        with open(files_changed[0], "r") as f:
            actual_content = f.read()
        
        # Read the expected content
        with open(python_expected_file, "r") as f:
            expected_content = f.read()

        # Compare the actual content with the expected content
        self.assertEqual(actual_content, expected_content)


    def test_typescript_function_insertion(self) -> None:
        """Test inserting content after a TypeScript function"""
        # Define paths for original and expected TypeScript files
        typescript_mock_path = os.path.join(os.path.dirname(__file__), "mock/insert_after_function_mock_typescript.json")
        typescript_original_file = os.path.join(os.path.dirname(__file__), "mock/price_chart_widget.ts")
        typescript_expected_file = os.path.join(os.path.dirname(__file__), "mock/price_chart_widget_after.ts")
        
        # Copy original TypeScript file to temp directory
        typescript_temp_file = os.path.join(self.temp_dir, "price_chart_widget.ts")
        shutil.copy2(typescript_original_file, typescript_temp_file)
        
        # Load the TypeScript mock JSON file
        with open(typescript_mock_path, "r") as f:
            json_content = f.read()
        
        # Extract the JSON content using cutoff_string
        json_content = cutoff_string(json_content, "```json", "```")
        
        # Parse the JSON content
        changes_json = manual_json_parse(json_content)
        
        # Modify the file paths in the changes to point to our temp directory
        for change in changes_json["changes"]:
            if "filename" in change:
                original_path = change["filename"]
                filename = os.path.basename(original_path)
                change["filename"] = os.path.join(self.temp_dir, filename)
        
        # Apply the changes
        with patch('jrdev.file_utils.terminal_print') as mock_terminal_print:
            files_changed = apply_file_changes(changes_json)
        
        # Verify that the file was changed
        self.assertEqual(len(files_changed), 1)
        
        # Read the content of the changed file
        with open(files_changed[0], "r") as f:
            actual_content = f.read()
        
        # Read the expected content
        with open(typescript_expected_file, "r") as f:
            expected_content = f.read()
        
        # Compare the actual content with the expected content
        self.assertEqual(actual_content, expected_content)


if __name__ == "__main__":
    unittest.main()