import os
import sys
import unittest
import tempfile
import shutil

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from jrdev.file_operations.file_utils import cutoff_string, manual_json_parse, apply_file_changes


class TestReplaceOperation(unittest.TestCase):
    """Tests for REPLACE operation in file_utils.py"""

    def setUp(self) -> None:
        """Set up test environment"""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Define paths for test files
        self.mock_response_path = os.path.join(os.path.dirname(__file__), "tests/mock/replace_example1.txt")
        self.original_file = os.path.join(os.path.dirname(__file__), "tests/mock/replace_example1_start.h")
        self.expected_file = os.path.join(os.path.dirname(__file__), "tests/mock/replace_example1_end.h")
        
        # Copy original file to temp directory
        self.temp_file = os.path.join(self.temp_dir, "assetbox.h")
        shutil.copy2(self.original_file, self.temp_file)

    def tearDown(self) -> None:
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir)

    def test_replace_operation(self) -> None:
        """Test REPLACE operation with signature replacement"""
        # Load the mock response
        with open(self.mock_response_path, "r") as f:
            json_content = f.read()
        
        # Extract the JSON content using cutoff_string
        json_content = cutoff_string(json_content, "```json", "```")
        
        # Parse the JSON content
        changes_json = manual_json_parse(json_content)
        
        # Modify the file paths in the changes to point to our temp directory
        for change in changes_json["changes"]:
            if "filename" in change:
                change["filename"] = self.temp_file
        
        # Set self.maxDiff to None to see the full diff
        self.maxDiff = None
        
        # Apply the changes
        files_changed = apply_file_changes(changes_json)
        
        # Verify that the file was changed
        self.assertEqual(len(files_changed), 1)
        self.assertEqual(files_changed[0], self.temp_file)
        
        # Read the content of the changed file
        with open(self.temp_file, "r") as f:
            actual_content = f.read()
        
        # Read the expected content
        with open(self.expected_file, "r") as f:
            expected_content = f.read()
        
        # Compare the actual content with the expected content
        self.assertEqual(actual_content, expected_content)


if __name__ == "__main__":
    unittest.main()