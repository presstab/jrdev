import os
import sys
import unittest
import asyncio
import json
from typing import Any, Dict, List, Optional, cast
from unittest.mock import patch, MagicMock, AsyncMock

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.file_utils import *


class TestFileUtils(unittest.TestCase):
    """Tests for functions in file_utils.py"""
    
    jsonresponse_path: str

    def setUp(self) -> None:
        """Set up test environment"""
        self.jsonresponse_path = os.path.join(os.path.dirname(__file__), "../src/jrdev/jsonresponse_newfile.txt")

    def test_check_and_apply_code_changes(self) -> None:
        """Test check_and_apply_code_changes with sample JSON response"""
        # Load jsonresponse.txt content
        with open(self.jsonresponse_path, "r") as f:
            json_response: str = f.read()

        print(json_response)
        cutoff = cutoff_string(json_response, "```json", "```")
        print(f"cutoff:\n {cutoff}")

        new_files = manual_json_parse(cutoff)
        #print(f"parse_line_by_line:\n {parse_line_by_line}")
        if "files" in new_files:
            for file in new_files["files"]:
                full_path = f"{file['path']}{file['filename']}"
                write_string_to_file(full_path, file["content"])
        #check_and_apply_code_changes(json_response)


if __name__ == "__main__":
    unittest.main()