import os
import sys
import unittest
import tempfile
import shutil

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from jrdev.file_operations.file_utils import manual_json_parse, apply_file_changes


class TestCodeSnippetReplacement(unittest.TestCase):
    """Tests for code_snippet option in REPLACE operation"""

    def setUp(self) -> None:
        """Set up test environment"""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Define test file with content
        self.test_file = os.path.join(self.temp_dir, "test_file.py")
        with open(self.test_file, "w") as f:
            f.write("""def hello_world():
    print("Hello, World!")
    
    # Some comment
    value = 42
    return value

def another_function():
    # Do something else
    pass
""")

    def tearDown(self) -> None:
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir)

    def test_code_snippet_replacement(self) -> None:
        """Test REPLACE operation with code_snippet option"""
        # Define the changes JSON with code_snippet
        changes_json = {
            "changes": [
                {
                    "operation": "REPLACE",
                    "filename": self.test_file,
                    "target_type": "BLOCK",
                    "target_reference": {
                        "code_snippet": "    # Some comment\n    value = 42"
                    },
                    "new_content": "    # Updated comment\n    value = 100"
                }
            ]
        }
        
        # Apply the changes
        files_changed = apply_file_changes(changes_json)
        
        # Verify that the file was changed
        self.assertEqual(len(files_changed), 1)
        self.assertEqual(files_changed[0], self.test_file)
        
        # Read the content of the changed file
        with open(self.test_file, "r") as f:
            actual_content = f.read()
        
        # Normalize the content by removing extra whitespace and empty lines
        def normalize_content(content):
            lines = []
            for line in content.splitlines():
                # Keep non-empty lines and their whitespace
                if line.strip():
                    lines.append(line.rstrip())
                # For empty lines, just add them without any whitespace
                elif line:
                    lines.append("")
            return '\n'.join(lines)
        
        actual_normalized = normalize_content(actual_content)
        expected_normalized = normalize_content("""def hello_world():
    print("Hello, World!")
    
    # Updated comment
    value = 100
    return value

def another_function():
    # Do something else
    pass
""")
        
        # Compare normalized versions
        self.assertEqual(actual_normalized, expected_normalized)

    def test_multiline_code_snippet_replacement(self) -> None:
        """Test REPLACE operation with multiline code_snippet"""
        # Define the changes JSON with a multiline code_snippet
        changes_json = {
            "changes": [
                {
                    "operation": "REPLACE",
                    "filename": self.test_file,
                    "target_reference": {
                        "code_snippet": "def hello_world():\n    print(\"Hello, World!\")\n    \n    # Some comment\n    value = 42\n    return value"
                    },
                    "new_content": "def hello_world():\n    print(\"Hello, Modified World!\")\n\n    # Updated function\n    value = 100\n    return value"
                }
            ]
        }
        
        # Apply the changes
        files_changed = apply_file_changes(changes_json)
        
        # Verify that the file was changed
        self.assertEqual(len(files_changed), 1)
        
        # Read the content of the changed file
        with open(self.test_file, "r") as f:
            actual_content = f.read()
        
        # Normalize the content
        def normalize_content(content):
            lines = []
            for line in content.splitlines():
                # Keep non-empty lines and their whitespace
                if line.strip():
                    lines.append(line.rstrip())
                # For empty lines, just add them without any whitespace
                elif line:
                    lines.append("")
            return '\n'.join(lines)
        
        actual_normalized = normalize_content(actual_content)
        expected_normalized = normalize_content("""def hello_world():
    print("Hello, Modified World!")

    # Updated function
    value = 100
    return value

def another_function():
    # Do something else
    pass
""")
        
        # Compare normalized versions
        self.assertEqual(actual_normalized, expected_normalized)


if __name__ == "__main__":
    unittest.main()