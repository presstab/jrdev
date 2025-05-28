import os
import sys
import unittest
from typing import List

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.file_operations.diff_markup import apply_diff_markup, remove_diff_markup
from jrdev.file_operations.diff_utils import create_diff

class TestDiffMarkup(unittest.TestCase):

    def _run_round_trip_test(self, original_content: str, new_content: str, filepath: str = "test_file.txt"):
        diff_lines = create_diff(original_content, new_content, filepath)
        marked_up_lines = apply_diff_markup(original_content, diff_lines)
        reconstructed_content = remove_diff_markup(marked_up_lines)
        
        self.assertEqual(reconstructed_content, new_content, 
                         f"\nRound-trip failed for:\nOriginal:\n'''{original_content}'''\nExpected New:\n'''{new_content}'''\nGenerated Diff (first 10 lines):\n{diff_lines[:10]}\nMarked Up Lines:\n{marked_up_lines}\nReconstructed Content:\n'''{reconstructed_content}'''")

    # --- Round Trip Tests ---
    def test_round_trip_no_changes(self):
        original = "line1\nline2\nline3"
        new = "line1\nline2\nline3"
        self._run_round_trip_test(original, new)

    def test_round_trip_no_changes_trailing_newline(self):
        original = "line1\nline2\nline3\n"
        new = "line1\nline2\nline3\n"
        self._run_round_trip_test(original, new)
        
    def test_round_trip_addition_middle(self):
        original = "line1\nline3"
        new = "line1\nline2_added\nline3"
        self._run_round_trip_test(original, new)

    def test_round_trip_addition_start(self):
        original = "line2\nline3"
        new = "line1_added\nline2\nline3"
        self._run_round_trip_test(original, new)

    def test_round_trip_addition_end(self):
        original = "line1\nline2"
        new = "line1\nline2\nline3_added"
        self._run_round_trip_test(original, new)

    def test_round_trip_deletion_middle(self):
        original = "line1\nline2_to_delete\nline3"
        new = "line1\nline3"
        self._run_round_trip_test(original, new)

    def test_round_trip_deletion_start(self):
        original = "line1_to_delete\nline2\nline3"
        new = "line2\nline3"
        self._run_round_trip_test(original, new)

    def test_round_trip_deletion_end(self):
        original = "line1\nline2\nline3_to_delete"
        new = "line1\nline2"
        self._run_round_trip_test(original, new)

    def test_round_trip_modification_middle(self):
        original = "line1\nold_line2\nline3"
        new = "line1\nnew_line2\nline3"
        self._run_round_trip_test(original, new)
        
    def test_round_trip_modification_start(self):
        original = "old_line1\nline2\nline3"
        new = "new_line1\nline2\nline3"
        self._run_round_trip_test(original, new)

    def test_round_trip_modification_end(self):
        original = "line1\nline2\nold_line3"
        new = "line1\nline2\nnew_line3"
        self._run_round_trip_test(original, new)

    def test_round_trip_add_to_empty(self):
        original = ""
        new = "new_line1\nnew_line2"
        # Note: This test may fail if the apply_diff_markup implementation (being tested)
        # has issues handling diffs for additions to empty files (e.g., '@@ -0,0 ...').
        # A failing test here would correctly indicate such a bug in apply_diff_markup.
        self._run_round_trip_test(original, new)

    def test_round_trip_delete_to_empty(self):
        original = "line1_to_delete\nline2_to_delete"
        new = ""
        self._run_round_trip_test(original, new)

    def test_round_trip_complex_changes(self):
        original = "alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot"
        new = "alpha_modified\ncharlie\ndelta_new_inserted\necho_modified\ngolf_new_end"
        self._run_round_trip_test(original, new)
        
    def test_round_trip_empty_strings(self):
        self._run_round_trip_test("", "")

    def test_round_trip_single_line_no_change(self):
        self._run_round_trip_test("hello", "hello")

    def test_round_trip_single_line_to_empty(self):
        self._run_round_trip_test("hello", "")

    def test_round_trip_empty_to_single_line(self):
        # Note: Similar to test_round_trip_add_to_empty, this may fail if apply_diff_markup
        # does not correctly handle diffs starting from an empty original content.
        self._run_round_trip_test("", "hello")
        
    def test_round_trip_single_line_modification(self):
        self._run_round_trip_test("hello world", "hello universe")

    def test_round_trip_multiple_lines_to_single_line(self):
        original = "line1\nline2\nline3"
        new = "single line"
        self._run_round_trip_test(original, new)

    def test_round_trip_single_line_to_multiple_lines(self):
        original = "single line"
        new = "line1\nline2\nline3"
        self._run_round_trip_test(original, new)

    # --- Specific apply_diff_markup Tests ---
    def test_apply_markup_simple_addition(self):
        original_content = "line1\nline3"
        diff = [
            "--- a/file.txt",
            "+++ b/file.txt",
            "@@ -1,2 +1,3 @@",
            " line1",
            "+line2_added",
            " line3"
        ]
        expected_markup = [
            " line1",
            "+line2_added",
            " line3"
        ]
        self.assertEqual(apply_diff_markup(original_content, diff), expected_markup)

    def test_apply_markup_simple_deletion(self):
        original_content = "line1\nline2_to_delete\nline3"
        diff = [
            "--- a/file.txt",
            "+++ b/file.txt",
            "@@ -1,3 +1,2 @@",
            " line1",
            "-line2_to_delete",
            " line3"
        ]
        expected_markup = [
            " line1",
            "-line2_to_delete",
            " line3"
        ]
        self.assertEqual(apply_diff_markup(original_content, diff), expected_markup)

    def test_apply_markup_simple_replacement(self):
        original_content = "line1\nold_line2\nline3"
        diff = [
            "--- a/file.txt",
            "+++ b/file.txt",
            "@@ -1,3 +1,3 @@",
            " line1",
            "-old_line2",
            "+new_line2",
            " line3"
        ]
        expected_markup = [
            " line1",
            "-old_line2",
            "+new_line2",
            " line3"
        ]
        self.assertEqual(apply_diff_markup(original_content, diff), expected_markup)

    def test_apply_markup_add_to_empty(self):
        original_content = ""
        diff = [
            "--- a/file.txt",
            "+++ b/file.txt",
            "@@ -0,0 +1,2 @@", 
            "+new_line1",
            "+new_line2"
        ]
        # This test asserts the expected *correct* behavior for adding to an empty file.
        # If the apply_diff_markup implementation being tested has a bug with '@@ -0,0 ...' diffs
        # (e.g., returning an empty list), this test will fail, thereby identifying the issue.
        expected_markup = [
            "+new_line1",
            "+new_line2"
        ]
        self.assertEqual(apply_diff_markup(original_content, diff), expected_markup)

    def test_apply_markup_delete_all_to_empty(self):
        original_content = "line1\nline2"
        diff = [
            "--- a/file.txt",
            "+++ b/file.txt",
            "@@ -1,2 +0,0 @@",
            "-line1",
            "-line2"
        ]
        expected_markup = [
            "-line1",
            "-line2"
        ]
        self.assertEqual(apply_diff_markup(original_content, diff), expected_markup)
        
    def test_apply_markup_insertion_at_eof(self):
        original_content = "line1"
        diff = [
            "--- a/file.txt",
            "+++ b/file.txt",
            "@@ -1,1 +1,2 @@",
            " line1",
            "+line2_added_at_end"
        ]
        expected_markup = [
            " line1",
            "+line2_added_at_end"
        ]
        self.assertEqual(apply_diff_markup(original_content, diff), expected_markup)

    # --- Specific remove_diff_markup Tests ---
    def test_remove_markup_simple_addition(self):
        marked_up = [" line1", "+line2_added", " line3"]
        expected_content = "line1\nline2_added\nline3"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_simple_deletion(self):
        marked_up = [" line1", "-line2_deleted", " line3"]
        expected_content = "line1\nline3"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_simple_replacement(self):
        marked_up = [" line1", "-old_line2", "+new_line2", " line3"]
        expected_content = "line1\nnew_line2\nline3"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_all_added(self):
        marked_up = ["+line1", "+line2", "+line3"]
        expected_content = "line1\nline2\nline3"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_all_deleted(self):
        marked_up = ["-line1", "-line2", "-line3"]
        expected_content = "" 
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_all_context(self):
        marked_up = [" line1", " line2", " line3"]
        expected_content = "line1\nline2\nline3"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_empty_input(self):
        marked_up: List[str] = []
        expected_content = ""
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_mixed_complex(self):
        marked_up = [
            "+added_at_start",
            " context1",
            "-deleted_line",
            " context2",
            "-old_replaced",
            "+new_replaced",
            "+another_added_line",
            " context3"
        ]
        expected_content = "added_at_start\ncontext1\ncontext2\nnew_replaced\nanother_added_line\ncontext3"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

    def test_remove_markup_line_with_no_prefix(self):
        # Tests behavior for lines that might have had their prefix accidentally removed by a user.
        # Based on the provided remove_diff_markup implementation, these are added as raw lines.
        marked_up = ["no_prefix_line", " another_line_with_space_prefix"]
        expected_content = "no_prefix_line\nanother_line_with_space_prefix"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)
        
    def test_remove_markup_line_with_trailing_newline_in_list_item(self):
        # The remove_diff_markup function internally strips '\n' from each input line.
        marked_up = ["+line1\n", " line2\n", "-line3\n"]
        expected_content = "line1\nline2"
        self.assertEqual(remove_diff_markup(marked_up), expected_content)

if __name__ == '__main__':
    unittest.main()
