import re
import os
from difflib import SequenceMatcher
import fnmatch
import glob

from jrdev.ui import terminal_print, PrintType

def requested_files(text):
    match = re.search(r"get_files\s+(\[.*?\])", text, re.DOTALL)
    if match:
        file_list_str = match.group(1)
        # Parse the file list string to get list of file paths
        # Strip any extra quotes and spaces to handle various formats
        file_list_str = file_list_str.replace(
            "'", '"'
        )  # Standardize on double quotes
        file_list = eval(
            file_list_str
        )  # Using eval since we have a valid list syntax
        return file_list

    return []


def find_similar_file(file_path):
    """
    Attempts to find a similar file when the exact path doesn't match.

    Args:
        file_path: The original file path that doesn't exist

    Returns:
        str: Path to a similar file if found, None otherwise
    """
    # Get the original filename and parent directories
    original_filename = os.path.basename(file_path)
    original_dirname = os.path.dirname(file_path)

    # Strategy 1: Look for exact filename in different directories
    try:
        # Search for files with matching name anywhere in the current directory tree
        matches = []
        for root, _, files in os.walk('.'):
            if original_filename in files:
                matches.append(os.path.join(root, original_filename))

        # If we found exactly one match, return it
        if len(matches) == 1:
            return matches[0]

        # If we found multiple matches, try to find the closest directory match
        if len(matches) > 1:
            # Sort matches by similarity of directory structure
            matches.sort(key=lambda m: SequenceMatcher(None,
                                                       os.path.dirname(m),
                                                       original_dirname).ratio(),
                         reverse=True)
            # Return the most similar match
            return matches[0]
    except Exception:
        pass

    # Strategy 2: Look for similar filenames in the same directory
    try:
        # Only proceed if the directory exists
        if os.path.exists(original_dirname):
            # Get all files in the directory
            files_in_dir = [f for f in os.listdir(original_dirname)
                            if os.path.isfile(os.path.join(original_dirname, f))]

            # Find similar filenames using fuzzy matching
            if files_in_dir:
                # Sort by similarity score to original filename
                similar_files = sorted(files_in_dir,
                                       key=lambda f: SequenceMatcher(None, f, original_filename).ratio(),
                                       reverse=True)

                # If best match has a similarity ratio > 0.6, return it
                best_match = similar_files[0]
                if SequenceMatcher(None, best_match, original_filename).ratio() > 0.6:
                    return os.path.join(original_dirname, best_match)
    except Exception:
        pass

    # Strategy 3: Try glob matching for partial patterns
    try:
        # Create glob pattern based on file extension
        ext = os.path.splitext(original_filename)[1]
        if ext:
            # Try to find files with same extension in similar directories
            pattern = f"**/*{ext}"
            matches = glob.glob(pattern, recursive=True)

            if matches:
                # Sort by filename similarity
                matches.sort(key=lambda m: SequenceMatcher(None,
                                                           os.path.basename(m),
                                                           original_filename).ratio(),
                             reverse=True)

                # Return the most similar match if it's reasonably close
                best_match = matches[0]
                if SequenceMatcher(None, os.path.basename(best_match), original_filename).ratio() > 0.5:
                    return best_match
    except Exception:
        pass

    # No similar file found
    return None


def get_file_contents(file_list):
    file_contents = {}
    for file_path in file_list:
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, "r") as f:
                    file_contents[file_path] = f.read()
            else:
                # Try to find a similar file when the exact path doesn't match
                similar_file = find_similar_file(file_path)
                if similar_file:
                    terminal_print(f"\nFound similar file: {similar_file} instead of {file_path}", PrintType.WARNING)
                    with open(similar_file, "r") as f:
                        file_contents[file_path] = f.read()
                else:
                    file_contents[file_path] = (
                        f"Error: File not found: {file_path}"
                    )
        except Exception as e:
            file_contents[file_path] = (
                f"Error reading file {file_path}: {str(e)}"
            )

    # Format the file contents as a string
    formatted_content = ""
    for path, content in file_contents.items():
        formatted_content += f"\n\n--- {path} ---\n{content}"

    return formatted_content


async def check_and_apply_code_changes(self, response_text):
    """Check if response contains code change JSON and apply changes if approved."""
    try:
        # First check for incomplete markdown code blocks like in ```json\n{\n    "changes": [\n        {\n
        if re.search(r'```(?:json)?\s*\{\s*["\'](?:file_changes|changes)["\']?\s*:\s*\[', response_text):
            terminal_print("\nDetected incomplete JSON code block. Attempting to process...", PrintType.INFO)
            # Try to parse what we have so far as JSON
            try:
                # Extract everything after the opening markdown block
                partial_json = re.search(r'```(?:json)?\s*(\{[\s\S]*)', response_text)
                if partial_json:
                    # Clean up and complete the JSON if it's incomplete
                    json_str = partial_json.group(1).strip()
                    if not json_str.endswith('}'):
                        # It's incomplete, add closing brackets to make it valid
                        if '"changes"' in json_str or "'changes'" in json_str:
                            json_str = json_str + '{}]}'
                        else:
                            json_str = json_str + '{}]}'

                    # Now try parsing the completed JSON
                    import json
                    code_changes = json.loads(json_str)
                    changes_key = "file_changes" if "file_changes" in code_changes else "changes"

                    # If we got here, we have a valid JSON object, continue with normal processing
                    if changes_key in code_changes and isinstance(code_changes[changes_key], list):
                        # But there are no actual changes (we added empty ones), so return
                        if len(code_changes[changes_key]) == 0:
                            terminal_print("No complete changes found in partial JSON.", PrintType.WARNING)
                            return
            except:
                # If this fails, continue with normal processing
                pass

        # Strip markdown code blocks if present
        cleaned_text = re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', r'\1', response_text)

        # Look for JSON structure in the response with either file_changes or changes field
        json_match = re.search(r'(\{[\s\S]*?(?:"file_changes"|"changes")\s*?:[\s\S]*?\})', cleaned_text)
        if not json_match:
            return

        json_str = json_match.group(1)

        try:
            # Parse the JSON
            import json
            code_changes = json.loads(json_str)

            # Handle either "file_changes" or "changes" keys
            changes_key = "file_changes" if "file_changes" in code_changes else "changes"

            # Verify it has the expected structure
            if changes_key not in code_changes or not isinstance(code_changes[changes_key], list):
                return

            terminal_print("\nCode changes detected. Processing each change...", PrintType.INFO)

            # Process each change
            for i, change in enumerate(code_changes[changes_key]):
                # Verify required fields are present based on change_type
                if "filename" not in change or "change_type" not in change:
                    terminal_print(f"Change #{i + 1} missing required fields, skipping...", PrintType.WARNING)
                    continue

                filename = change["filename"]
                change_type = change["change_type"]

                # Get file content if it exists
                file_content = []
                file_exists = os.path.exists(filename)
                if file_exists:
                    with open(filename, "r") as f:
                        file_content = f.readlines()

                # Create a preview of the change
                preview = self.create_change_preview(change, file_content, file_exists)

                # Ask for user approval
                terminal_print(f"\nProposed change #{i + 1} for {filename} ({change_type}):", PrintType.HEADER)
                terminal_print(preview, PrintType.INFO)
                approval = input("Apply this change? (y/n): ").strip().lower()

                if approval == 'y':
                    # Apply the change
                    success = self.apply_change(change, file_content)
                    if success:
                        terminal_print(f"Change applied to {filename}", PrintType.SUCCESS)
                    else:
                        terminal_print(f"Failed to apply change to {filename}", PrintType.ERROR)
                else:
                    terminal_print(f"Change to {filename} skipped", PrintType.INFO)

        except json.JSONDecodeError as e:
            # Try to clean up the JSON string more aggressively and try again
            try:
                # Remove any extra text before and after the JSON object
                cleaned_json = re.search(r'(\{[\s\S]*\})', json_str)
                if cleaned_json:
                    code_changes = json.loads(cleaned_json.group(1))
                    # Continue processing with the same code as above...
                    changes_key = "file_changes" if "file_changes" in code_changes else "changes"

                    if changes_key not in code_changes or not isinstance(code_changes[changes_key], list):
                        return

                    terminal_print("\nCode changes detected. Processing each change...", PrintType.INFO)

                    for i, change in enumerate(code_changes[changes_key]):
                        if "filename" not in change or "change_type" not in change:
                            terminal_print(f"Change #{i + 1} missing required fields, skipping...",
                                           PrintType.WARNING)
                            continue

                        filename = change["filename"]
                        change_type = change["change_type"]

                        file_content = []
                        file_exists = os.path.exists(filename)
                        if file_exists:
                            with open(filename, "r") as f:
                                file_content = f.readlines()

                        preview = self.create_change_preview(change, file_content, file_exists)

                        terminal_print(f"\nProposed change #{i + 1} for {filename} ({change_type}):",
                                       PrintType.HEADER)
                        terminal_print(preview, PrintType.INFO)
                        approval = input("Apply this change? (y/n): ").strip().lower()

                        if approval == 'y':
                            success = self.apply_change(change, file_content)
                            if success:
                                terminal_print(f"Change applied to {filename}", PrintType.SUCCESS)
                            else:
                                terminal_print(f"Failed to apply change to {filename}", PrintType.ERROR)
                        else:
                            terminal_print(f"Change to {filename} skipped", PrintType.INFO)
                else:
                    return
            except Exception:
                # If second attempt fails, just return
                return
        except Exception as e:
            terminal_print(f"Error processing code changes: {str(e)}", PrintType.ERROR)

    except Exception as e:
        terminal_print(f"Error checking for code changes: {str(e)}", PrintType.ERROR)


def create_change_preview(change, file_content, file_exists):
    """Create a preview of the proposed change."""
    try:
        change_type = change["change_type"]
        filename = change["filename"]
        preview = []

        if change_type == "replace":
            if not file_exists:
                return f"Error: Cannot replace content in non-existent file: {filename}"

            if "start_line" not in change or "end_line" not in change or "replacement" not in change:
                return "Error: Missing required fields for replacement"

            start_line = change["start_line"]
            end_line = change["end_line"]
            replacement = change["replacement"]

            # Ensure start and end lines are valid
            if start_line < 1 or end_line > len(file_content) or start_line > end_line:
                return f"Error: Invalid line range ({start_line}-{end_line}) for file with {len(file_content)} lines"

            # Create preview with context (a few lines before and after)
            context_lines = 3
            preview.append("--- Original ---")
            for i in range(max(1, start_line - context_lines),
                           min(len(file_content) + 1, end_line + context_lines + 1)):
                line = file_content[i - 1].rstrip('\n')
                prefix = "* " if start_line <= i <= end_line else "  "
                preview.append(f"{prefix}{i}: {line}")

            preview.append("\n+++ Replacement +++")
            for i, line in enumerate(replacement):
                preview.append(f"  {start_line + i}: {line}")

        elif change_type == "insert":
            if not file_exists:
                return f"Error: Cannot insert content into non-existent file: {filename}"

            if "after_line" not in change or "content" not in change:
                return "Error: Missing required fields for insertion"

            after_line = change["after_line"]
            content = change["content"]

            # Ensure after_line is valid
            if after_line < 0 or after_line > len(file_content):
                return f"Error: Invalid line number {after_line} for file with {len(file_content)} lines"

            # Create preview with context
            context_lines = 3
            preview.append("--- Context ---")
            for i in range(max(1, after_line - context_lines + 1), min(len(file_content) + 1, after_line + 2)):
                line = file_content[i - 1].rstrip('\n')
                prefix = "* " if i == after_line + 1 else "  "
                preview.append(f"{prefix}{i}: {line}")

            preview.append("\n+++ Insertion (after line {}) +++".format(after_line))
            for i, line in enumerate(content):
                preview.append(f"+ {line}")

        elif change_type == "delete":
            if not file_exists:
                return f"Error: Cannot delete content from non-existent file: {filename}"

            if "start_line" not in change or "end_line" not in change:
                return "Error: Missing required fields for deletion"

            start_line = change["start_line"]
            end_line = change["end_line"]

            # Ensure start and end lines are valid
            if start_line < 1 or end_line > len(file_content) or start_line > end_line:
                return f"Error: Invalid line range ({start_line}-{end_line}) for file with {len(file_content)} lines"

            # Create preview with context
            context_lines = 3
            preview.append("--- Lines to delete ---")
            for i in range(max(1, start_line - context_lines),
                           min(len(file_content) + 1, end_line + context_lines + 1)):
                line = file_content[i - 1].rstrip('\n')
                prefix = "- " if start_line <= i <= end_line else "  "
                preview.append(f"{prefix}{i}: {line}")

        return "\n".join(preview)

    except Exception as e:
        return f"Error creating preview: {str(e)}"

def apply_change(change, file_content):
    """Apply the approved change to the file."""
    try:
        filename = change["filename"]
        change_type = change["change_type"]

        if change_type == "replace":
            start_line = change["start_line"]
            end_line = change["end_line"]
            replacement = change["replacement"]

            # Apply replacement
            new_content = file_content[:start_line - 1] + [line + '\n' for line in replacement] + file_content[
                                                                                                  end_line:]

        elif change_type == "insert":
            after_line = change["after_line"]
            content = change["content"]

            # Apply insertion
            new_content = file_content[:after_line] + [line + '\n' for line in content] + file_content[after_line:]

        elif change_type == "delete":
            start_line = change["start_line"]
            end_line = change["end_line"]

            # Apply deletion
            new_content = file_content[:start_line - 1] + file_content[end_line:]

        else:
            terminal_print(f"Unknown change type: {change_type}", PrintType.ERROR)
            return False

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        # Write the modified content back to the file
        with open(filename, "w") as f:
            f.writelines(new_content)

        return True

    except Exception as e:
        terminal_print(f"Error applying change: {str(e)}", PrintType.ERROR)
        return False