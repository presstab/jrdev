import os
import sys
import unittest

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.utils.string_utils import (
    find_code_snippet,
    contains_chinese,
    is_valid_url,
    is_valid_name,
    is_valid_env_key,
    is_valid_cost,
    is_valid_context_window,
)

class TestStringUtils(unittest.TestCase):

    # --- Tests for is_valid_url ---
    def test_is_valid_url_valid(self):
        self.assertTrue(is_valid_url("http://example.com"))
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("https://www.example.com"))
        self.assertTrue(is_valid_url("http://example.co.uk/path"))
        self.assertTrue(is_valid_url("https://example.com?query=123"))
        self.assertTrue(is_valid_url("http://127.0.0.1:8000"))

    def test_is_valid_url_invalid(self):
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url("example.com"))
        self.assertFalse(is_valid_url("http:// example.com"))
        self.assertFalse(is_valid_url("http//example.com"))
        self.assertFalse(is_valid_url(None))
        self.assertFalse(is_valid_url(123))

    # --- Tests for is_valid_name ---
    def test_is_valid_name_valid(self):
        self.assertTrue(is_valid_name("valid-name"))
        self.assertTrue(is_valid_name("ValidName123"))
        self.assertTrue(is_valid_name("valid_name"))
        self.assertTrue(is_valid_name("a"))
        self.assertTrue(is_valid_name("a" * 64))
        self.assertTrue(is_valid_name("valid/name"))

    def test_is_valid_name_invalid(self):
        self.assertFalse(is_valid_name(""))
        self.assertFalse(is_valid_name("a" * 65))
        self.assertFalse(is_valid_name("invalid name"))
        self.assertFalse(is_valid_name("invalid\tname"))
        self.assertFalse(is_valid_name(None))

    # --- Tests for is_valid_env_key ---
    def test_is_valid_env_key_valid(self):
        self.assertTrue(is_valid_env_key("VALID_KEY"))
        self.assertTrue(is_valid_env_key("VALID-KEY-123"))
        self.assertTrue(is_valid_env_key("a"))
        self.assertTrue(is_valid_env_key("a" * 128))

    def test_is_valid_env_key_invalid(self):
        self.assertFalse(is_valid_env_key(""))
        self.assertFalse(is_valid_env_key("a" * 129))
        self.assertFalse(is_valid_env_key("invalid key"))
        self.assertFalse(is_valid_env_key("invalid/key"))
        self.assertFalse(is_valid_env_key(None))

    # --- Tests for is_valid_cost ---
    def test_is_valid_cost_valid(self):
        self.assertTrue(is_valid_cost(0.0))
        self.assertTrue(is_valid_cost(100.50))
        self.assertTrue(is_valid_cost(1000.0))

    def test_is_valid_cost_invalid(self):
        self.assertFalse(is_valid_cost(-0.1))
        self.assertFalse(is_valid_cost(1000.1))
        self.assertFalse(is_valid_cost("not a float"))
        self.assertFalse(is_valid_cost(None))

    # --- Tests for is_valid_context_window ---
    def test_is_valid_context_window_valid(self):
        self.assertTrue(is_valid_context_window(1))
        self.assertTrue(is_valid_context_window(100000))
        self.assertTrue(is_valid_context_window(1_000_000_000))

    def test_is_valid_context_window_invalid(self):
        self.assertFalse(is_valid_context_window(0))
        self.assertFalse(is_valid_context_window(1_000_000_001))
        self.assertFalse(is_valid_context_window("not an int"))
        self.assertFalse(is_valid_context_window(None))

    # --- Tests for contains_chinese ---
    def test_contains_chinese(self):
        self.assertTrue(contains_chinese("你好"))
        self.assertTrue(contains_chinese("hello你好world"))
        self.assertFalse(contains_chinese("hello world"))
        self.assertFalse(contains_chinese("!@#$%^&*()"))
        self.assertFalse(contains_chinese(""))

    # --- Tests for find_code_snippet ---
    def test_find_code_snippet(self):
        lines = [
            "def hello():",
            "    print('Hello, world!')",
            "",
            "def goodbye():",
            "    print('Goodbye, world!')",
        ]

        # Test single-line snippet
        self.assertEqual(find_code_snippet(lines, "print('Hello, world!')"), (1, 2))

        # Test multi-line snippet
        snippet = "def goodbye():\n    print('Goodbye, world!')"
        self.assertEqual(find_code_snippet(lines, snippet), (3, 5))

        # Test snippet not found
        self.assertEqual(find_code_snippet(lines, "print('not found')"), (-1, -1))

        # Test with different indentation
        snippet_different_indent = "def goodbye():\n  print('Goodbye, world!')"
        self.assertEqual(find_code_snippet(lines, snippet_different_indent), (3, 5))

        # Test empty snippet
        self.assertEqual(find_code_snippet(lines, ""), (-1, -1))

        # Test empty lines
        self.assertEqual(find_code_snippet([], "def hello():"), (-1, -1))

if __name__ == '__main__':
    unittest.main()
