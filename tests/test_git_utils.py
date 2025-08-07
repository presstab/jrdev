import unittest
import os
import shutil
import subprocess
import sys
from unittest.mock import patch

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.utils import git_utils

class TestGitUtils(unittest.TestCase):
    def setUp(self):
        """Set up a temporary git repository for testing."""
        self.test_dir = os.path.abspath("test_repo")
        os.makedirs(self.test_dir, exist_ok=True)
        os.chdir(self.test_dir)
        subprocess.call(["git", "init"])
        subprocess.call(["git", "config", "user.email", "test@example.com"])
        subprocess.call(["git", "config", "user.name", "Test User"])

    def tearDown(self):
        """Clean up the temporary git repository."""
        os.chdir(os.path.join(self.test_dir, ".."))
        shutil.rmtree(self.test_dir)

    def test_get_git_status(self):
        # 1. Test empty repository
        staged, unstaged, untracked = git_utils.get_git_status()
        self.assertEqual(staged, [])
        self.assertEqual(unstaged, [])
        self.assertEqual(untracked, set())

        # Create files
        file1 = "file1.txt"
        file2 = "file2.txt"
        file3 = "file3.txt"

        with open(file1, "w") as f:
            f.write("content1")
        with open(file2, "w") as f:
            f.write("content2")
        with open(file3, "w") as f:
            f.write("content3")

        # 2. Test with untracked files
        staged, unstaged, untracked = git_utils.get_git_status()
        self.assertEqual(staged, [])
        self.assertEqual(sorted(unstaged), [file1, file2, file3])
        self.assertEqual(untracked, {file1, file2, file3})

        # 3. Test with a staged file
        subprocess.call(["git", "add", file1])
        staged, unstaged, untracked = git_utils.get_git_status()
        self.assertEqual(staged, [file1])
        self.assertEqual(sorted(unstaged), [file2, file3])
        self.assertEqual(untracked, {file2, file3})

        # 4. Commit the staged file
        subprocess.call(["git", "commit", "-m", "Initial commit"])
        staged, unstaged, untracked = git_utils.get_git_status()
        self.assertEqual(staged, [])
        self.assertEqual(sorted(unstaged), [file2, file3])
        self.assertEqual(untracked, {file2, file3})

        # 5. Modify a committed file
        with open(file1, "w") as f:
            f.write("modified content")
        staged, unstaged, untracked = git_utils.get_git_status()
        self.assertEqual(staged, [])
        self.assertEqual(sorted(unstaged), [file1, file2, file3])
        self.assertEqual(untracked, {file2, file3})

        # 6. Stage another file
        subprocess.call(["git", "add", file2])
        staged, unstaged, untracked = git_utils.get_git_status()
        self.assertEqual(staged, [file2])
        self.assertEqual(sorted(unstaged), [file1, file3])
        self.assertEqual(untracked, {file3})

        # 7. Modify a staged file (now both staged and unstaged)
        with open(file2, "w") as f:
            f.write("modified content 2")
        staged, unstaged, untracked = git_utils.get_git_status()
        self.assertEqual(staged, [file2])
        self.assertEqual(sorted(unstaged), [file1, file2, file3])
        self.assertEqual(untracked, {file3})

    def test_get_file_diff(self):
        file1 = "file1.txt"
        with open(file1, "w") as f:
            f.write("line 1\n")
            f.write("line 2\n")

        # 1. Untracked file
        diff = git_utils.get_file_diff(file1, is_untracked=True)
        self.assertIn("--- /dev/null", diff)
        self.assertIn("+++ b/file1.txt", diff)
        self.assertIn("+line 1", diff)
        self.assertIn("+line 2", diff)

        # Stage the file and commit
        subprocess.call(["git", "add", file1])
        subprocess.call(["git", "commit", "-m", "add file1"])

        # 2. Unchanged file
        diff = git_utils.get_file_diff(file1)
        self.assertEqual(diff, "")

        # 3. Modified (unstaged) file
        with open(file1, "a") as f:
            f.write("line 3\n")

        diff = git_utils.get_file_diff(file1)
        self.assertIn("--- a/file1.txt", diff)
        self.assertIn("+++ b/file1.txt", diff)
        self.assertIn("+line 3", diff)

        # 4. Staged file
        subprocess.call(["git", "add", file1])
        diff = git_utils.get_file_diff(file1, staged=True)
        self.assertIn("--- a/file1.txt", diff)
        self.assertIn("+++ b/file1.txt", diff)
        self.assertIn("+line 3", diff)

        # 5. Staged and then modified again (unstaged changes)
        with open(file1, "a") as f:
            f.write("line 4\n")

        # Check unstaged diff
        diff_unstaged = git_utils.get_file_diff(file1)
        self.assertIn("+line 4", diff_unstaged)
        self.assertNotIn("+line 3", diff_unstaged)

        # Check staged diff
        diff_staged = git_utils.get_file_diff(file1, staged=True)
        self.assertIn("+line 3", diff_staged)
        self.assertNotIn("+line 4", diff_staged)

    def test_get_current_branch(self):
        # Default branch is 'master' in git versions < 2.28.
        # It can be 'main' or other names in newer versions depending on global config.
        # Let's get the actual branch name instead of hardcoding 'master'.
        initial_branch = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip()

        self.assertEqual(git_utils.get_current_branch(), initial_branch)

        # Create and checkout a new branch
        subprocess.call(["git", "checkout", "-b", "new-branch"])
        self.assertEqual(git_utils.get_current_branch(), "new-branch")

    def test_file_operations(self):
        file1 = "ops_file.txt"
        initial_content = "initial content"
        modified_content = "modified content"

        with open(file1, "w") as f:
            f.write(initial_content)

        # 1. Test stage_file
        self.assertTrue(git_utils.stage_file(file1))
        staged, _, _ = git_utils.get_git_status()
        self.assertIn(file1, staged)

        # 2. Test unstage_file
        self.assertTrue(git_utils.unstage_file(file1))
        staged, unstaged, _ = git_utils.get_git_status()
        self.assertNotIn(file1, staged)
        self.assertIn(file1, unstaged)

        # Commit the file to test reset
        subprocess.call(["git", "add", file1])
        subprocess.call(["git", "commit", "-m", "add ops_file"])

        # Modify the file
        with open(file1, "w") as f:
            f.write(modified_content)

        _, unstaged, _ = git_utils.get_git_status()
        self.assertIn(file1, unstaged)

        # 3. Test reset_unstaged_changes
        self.assertTrue(git_utils.reset_unstaged_changes(file1))
        _, unstaged, _ = git_utils.get_git_status()
        self.assertNotIn(file1, unstaged)

        with open(file1, "r") as f:
            content = f.read()
        self.assertEqual(content, initial_content)

    def test_perform_commit(self):
        # 1. Test successful commit
        file1 = "commit_file.txt"
        with open(file1, "w") as f:
            f.write("some content")

        subprocess.call(["git", "add", file1])

        commit_message = "Test commit"
        success, error = git_utils.perform_commit(commit_message)
        self.assertTrue(success)
        self.assertIsNone(error)

        # Verify the commit was made
        log_output = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"], text=True
        ).strip()
        self.assertEqual(log_output, commit_message)

        # 2. Test commit with no staged changes
        success, error = git_utils.perform_commit("Another commit")
        self.assertFalse(success)
        self.assertIsNotNone(error)
        self.assertIn("nothing to commit", error)

    def test_get_staged_diff(self):
        # 1. No staged changes
        diff = git_utils.get_staged_diff()
        self.assertEqual(diff, "")

        # 2. With staged changes
        file1 = "staged_diff_file.txt"
        with open(file1, "w") as f:
            f.write("initial\n")

        subprocess.call(["git", "add", file1])
        subprocess.call(["git", "commit", "-m", "add file"])

        with open(file1, "w") as f:
            f.write("modified\n")

        subprocess.call(["git", "add", file1])

        diff = git_utils.get_staged_diff()
        self.assertIn("--- a/staged_diff_file.txt", diff)
        self.assertIn("+++ b/staged_diff_file.txt", diff)
        self.assertIn("-initial", diff)
        self.assertIn("+modified", diff)

    def test_is_git_installed(self):
        # This will run in an environment where git is installed.
        self.assertTrue(git_utils.is_git_installed())

    @patch('jrdev.utils.git_utils.subprocess.check_output')
    def test_is_git_installed_not_found(self, mock_check_output):
        mock_check_output.side_effect = FileNotFoundError
        self.assertFalse(git_utils.is_git_installed())

    @patch('jrdev.utils.git_utils.subprocess.check_output')
    def test_is_git_installed_timeout(self, mock_check_output):
        mock_check_output.side_effect = subprocess.TimeoutExpired(cmd="git --version", timeout=1)
        self.assertFalse(git_utils.is_git_installed())

    def test_get_commit_history(self):
        # Test with a few commits
        file1 = "history_file1.txt"
        with open(file1, "w") as f: f.write("1")
        subprocess.call(["git", "add", file1])
        subprocess.call(["git", "commit", "-m", "commit 1"])

        file2 = "history_file2.txt"
        with open(file2, "w") as f: f.write("2")
        subprocess.call(["git", "add", file2])
        subprocess.call(["git", "commit", "-m", "commit 2"])

        history = git_utils.get_commit_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0][1], "commit 2")
        self.assertEqual(history[1][1], "commit 1")

    def test_get_commit_diff(self):
        file1 = "diff_commit_file.txt"
        with open(file1, "w") as f: f.write("content")
        subprocess.call(["git", "add", file1])
        subprocess.call(["git", "commit", "-m", "commit for diff"])

        history = git_utils.get_commit_history()
        commit_hash = history[0][0]

        # 1. Valid hash
        diff = git_utils.get_commit_diff(commit_hash)
        self.assertIsNotNone(diff)
        self.assertIn(commit_hash, diff)
        self.assertIn("commit for diff", diff)
        self.assertIn("+++ b/diff_commit_file.txt", diff)
        self.assertIn("+content", diff)

        # 2. Invalid hash
        diff_invalid = git_utils.get_commit_diff("invalidhash")
        self.assertIn("Error getting diff for invalidhash", diff_invalid)

if __name__ == "__main__":
    unittest.main()
