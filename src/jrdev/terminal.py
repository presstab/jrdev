#!/usr/bin/env python3

"""
Terminal interface for interacting with JrDev's LLM models
using OpenAI-compatible APIs.
"""
import asyncio
import os
import re
import sys
import platform
from pathlib import Path
from file_utils import *

from openai import AsyncOpenAI

import fnmatch
import glob
from difflib import SequenceMatcher

# Cross-platform readline support
try:
    if platform.system() == 'Windows':
        import pyreadline3 as readline
    else:
        import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

from jrdev.colors import Colors
from jrdev.commands import (handle_clear, handle_exit, handle_help,
                                handle_init, handle_model, handle_models,
                                handle_stateinfo)
from jrdev.models import AVAILABLE_MODELS
from jrdev.llm_requests import stream_request
from jrdev.treechart import generate_tree
from jrdev.ui import terminal_print, PrintType


class JrDevTerminal:
    def __init__(self):
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("VENICE_API_KEY")
        if not api_key:
            terminal_print("Error: VENICE_API_KEY not found in .env file", PrintType.ERROR)
            sys.exit(1)
            
        self.client = AsyncOpenAI(
            api_key=api_key,
            organization=None,
            project=None,
            base_url="https://api.venice.ai/api/v1",
        )
        self.model = "llama-3.3-70b"
        self.running = True
        self.messages = {} #model -> messages

        # Set up readline for command history
        self.history_file = os.path.expanduser("~/.jrdev_history")
        self.setup_readline()

    async def handle_command(self, command):
        cmd_parts = command.split()
        if not cmd_parts:
            return

        cmd = cmd_parts[0].lower()

        # Map commands to their handler functions
        command_handlers = {
            "/exit": handle_exit,
            "/model": handle_model,
            "/models": handle_models,
            "/stateinfo": handle_stateinfo,
            "/clear": handle_clear,
            "/init": handle_init,
            "/help": handle_help,
        }

        if cmd in command_handlers:
            return await command_handlers[cmd](self, cmd_parts)
        else:
            terminal_print(f"Unknown command: {cmd}", PrintType.ERROR)
            terminal_print("Type /help for available commands", PrintType.INFO)

    async def send_message(self, content):
        if not isinstance(content, str):
            terminal_print(f"Error: expected string but got {type(content)}", PrintType.ERROR)
            return
            
        # Read project context files if they exist
        project_files = {
            "filetree": "jrdev_filetree.txt",
            "filecontext": "jrdev_filecontext.md",
            "overview": "jrdev_overview.md",
            "code_change_example": "code_change_example.json"
        }

        project_context = {}
        for key, filename in project_files.items():
            try:
                if os.path.exists(filename):
                    with open(filename, "r") as f:
                        project_context[key] = f.read()
            except Exception as e:
                terminal_print(f"Warning: Could not read {filename}: {str(e)}", PrintType.WARNING)

        # Build the complete message
        dev_prompt_modifier = ("Consider the project that has been attached. An engineer for the project is asking you (a "
                           "master architect, and excellent engineer) for help or advice. Although the engineer is "
                           "asking a question to you, respond with an analysis of what would need to be done to "
                           "complete the task. This should be brief and should be written in a way that is readable for both "
                           "humans and llm's. If the user is asking about how to change code, IT IS REQUIRED that you retrieve"
                           " the full file before suggesting the code changes. Request files using the format: "
                           " 'get_files ['path/to/file1.txt', 'path/to/file2.cpp, etc]")

        user_additional_modifier = " Here is the user's question or instruction:"

        # Prepare message content with project context and prompt modifier
        user_message = f"{user_additional_modifier} {content}"

        if self.model not in self.messages:
            self.messages[self.model] = []

            # Append project context if available (only needed on first run)
            if project_context:
                for key, value in project_context.items():
                    user_message = f"{user_message}\n\n{key.upper()}:\n{value}"

            self.messages[self.model].append({"role": "system", "content": dev_prompt_modifier})

        self.messages[self.model].append({"role": "user", "content": user_message})

        # Show processing message
        model_name = self.model
        terminal_print(f"\n{model_name} is processing request...", PrintType.PROCESSING)

        try:
            response_text = await stream_request(self.client, self.model, self.messages[self.model])

            # Add a new line after the streaming completes
            terminal_print("", PrintType.INFO)

            # Add response to messages
            self.messages[self.model].append({"role": "assistant", "content": response_text})

            # Check for get_files request outside of think tags
            get_files_match = is_requesting_files(response_text)
            if get_files_match:
                file_list_str = get_files_match.group(1)
                terminal_print(f"\nDetected file request: {file_list_str}", PrintType.INFO)

                try:
                    # Parse the file list string to get list of file paths
                    # Strip any extra quotes and spaces to handle various formats
                    file_list_str = file_list_str.replace(
                        "'", '"'
                    )  # Standardize on double quotes
                    file_list = eval(
                        file_list_str
                    )  # Using eval since we have a valid list syntax

                    # Read the requested files
                    file_contents = {}
                    for file_path in file_list:
                        try:
                            if os.path.exists(file_path) and os.path.isfile(file_path):
                                with open(file_path, "r") as f:
                                    file_contents[file_path] = f.read()
                            else:
                                # Try to find a similar file when the exact path doesn't match
                                similar_file = self.find_similar_file(file_path)
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
                    files_content = ""
                    for path, content in file_contents.items():
                        files_content += f"\n\n--- {path} ---\n{content}"

                    # Send the file contents back to the LLM
                    follow_up_message = f"Previously requested files:{files_content}"
                    self.messages[self.model].append({"role": "user", "content": follow_up_message})

                    terminal_print(f"\nSending requested files to {model_name}...", PrintType.PROCESSING)

                    # Get the LLM's response to the files with streaming
                    follow_up_response = await stream_request(self.client, self.model, self.messages[self.model])

                    terminal_print("", PrintType.INFO)  # Add a new line after streaming

                    # Add complete response to messages
                    self.messages[self.model].append(
                        {"role": "assistant", "content": follow_up_response}
                    )

                    # Check for code change JSON in the follow-up response
                    # await self.check_and_apply_code_changes(follow_up_response)

                except Exception as e:
                    terminal_print(f"Error processing get_files request: {str(e)}", PrintType.ERROR)
            else:
                # Check for code change JSON in the response
                await self.check_and_apply_code_changes(response_text)
        except Exception as e:
            terminal_print(f"Error: {str(e)}", PrintType.ERROR)
            
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
                        terminal_print(f"Change #{i+1} missing required fields, skipping...", PrintType.WARNING)
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
                    terminal_print(f"\nProposed change #{i+1} for {filename} ({change_type}):", PrintType.HEADER)
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
                                terminal_print(f"Change #{i+1} missing required fields, skipping...", PrintType.WARNING)
                                continue
                                
                            filename = change["filename"]
                            change_type = change["change_type"]
                            
                            file_content = []
                            file_exists = os.path.exists(filename)
                            if file_exists:
                                with open(filename, "r") as f:
                                    file_content = f.readlines()
                            
                            preview = self.create_change_preview(change, file_content, file_exists)
                            
                            terminal_print(f"\nProposed change #{i+1} for {filename} ({change_type}):", PrintType.HEADER)
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
            
    def create_change_preview(self, change, file_content, file_exists):
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
                for i in range(max(1, start_line - context_lines), min(len(file_content) + 1, end_line + context_lines + 1)):
                    line = file_content[i-1].rstrip('\n')
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
                    line = file_content[i-1].rstrip('\n')
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
                for i in range(max(1, start_line - context_lines), min(len(file_content) + 1, end_line + context_lines + 1)):
                    line = file_content[i-1].rstrip('\n')
                    prefix = "- " if start_line <= i <= end_line else "  "
                    preview.append(f"{prefix}{i}: {line}")
            
            return "\n".join(preview)
            
        except Exception as e:
            return f"Error creating preview: {str(e)}"
            
    def apply_change(self, change, file_content):
        """Apply the approved change to the file."""
        try:
            filename = change["filename"]
            change_type = change["change_type"]
            
            if change_type == "replace":
                start_line = change["start_line"]
                end_line = change["end_line"]
                replacement = change["replacement"]
                
                # Apply replacement
                new_content = file_content[:start_line-1] + [line + '\n' for line in replacement] + file_content[end_line:]
                
            elif change_type == "insert":
                after_line = change["after_line"]
                content = change["content"]
                
                # Apply insertion
                new_content = file_content[:after_line] + [line + '\n' for line in content] + file_content[after_line:]
                
            elif change_type == "delete":
                start_line = change["start_line"]
                end_line = change["end_line"]
                
                # Apply deletion
                new_content = file_content[:start_line-1] + file_content[end_line:]
            
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

    def find_similar_file(self, file_path):
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
        
    def is_inside_think_tag(self, text):
        """Determine if the current position is inside a <think> tag."""
        # Count the number of opening and closing tags
        think_open = text.count("<think>")
        think_close = text.count("</think>")

        # If there are more opening tags than closing tags, we're inside a tag
        return think_open > think_close

    def filter_think_tags(self, text):
        """Remove content within <think></think> tags."""
        # Use regex to remove all <think>...</think> sections
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    def setup_readline(self):
        """Set up the readline module for command history."""
        if not READLINE_AVAILABLE:
            return
            
        try:
            # Enable history and tab completion
            readline.parse_and_bind("tab: complete")
            
            # Configure readline for better line wrapping
            readline.set_completer_delims(' \t\n;')
            
            # Configure line editing to handle long inputs better
            if hasattr(readline, 'set_screen_size'):
                # Get terminal size and set readline's screen size
                try:
                    import shutil
                    columns, _ = shutil.get_terminal_size()
                    # Set a large number of rows to ensure vertical scrolling
                    readline.set_screen_size(100, columns)
                except Exception:
                    # Fallback if terminal size detection fails
                    readline.set_screen_size(100, 120)

            # Load history if exists
            if os.path.exists(self.history_file):
                readline.read_history_file(self.history_file)
                # Set history length limit
                readline.set_history_length(1000)
        except Exception as e:
            terminal_print(f"Error setting up readline: {str(e)}", PrintType.ERROR)

    def save_history(self, input_text):
        """Save the input to history file."""
        if not READLINE_AVAILABLE or not input_text.strip():
            return
            
        try:
            readline.add_history(input_text)
            readline.write_history_file(self.history_file)
        except Exception as e:
            terminal_print(f"Error saving history: {str(e)}", PrintType.ERROR)

    def get_user_input(self):
        """Get user input with proper line wrapping."""
        # Make sure terminal can handle long lines by using better prompt
        prompt = f"\n{Colors.BOLD}{Colors.GREEN}> {Colors.RESET}"
        
        try:
            # Get terminal width to help with wrapping behavior
            import shutil
            term_width = shutil.get_terminal_size().columns
            # Adjust prompt width consideration
            prompt_len = 4  # Length of "> " without color codes
            available_width = term_width - prompt_len
            
            # If very narrow terminal, just use basic input
            if available_width < 20:
                return input(prompt)
                
            # Readline will use this width for wrapping
            if READLINE_AVAILABLE and hasattr(readline, 'set_screen_size'):
                readline.set_screen_size(100, available_width)
        except Exception:
            pass
            
        return input(prompt)
        
    async def run_terminal(self):
        terminal_print(f"JrDev Terminal (Model: {self.model})", PrintType.HEADER)
        terminal_print("Type a message to chat with the model", PrintType.INFO)
        terminal_print("Type /help for available commands", PrintType.INFO)
        terminal_print("Type /exit to quit", PrintType.INFO)
        if READLINE_AVAILABLE:
            terminal_print("Use up/down arrows to navigate command history", PrintType.INFO)

        while self.running:
            try:
                user_input = self.get_user_input()

                # Save to history
                self.save_history(user_input)

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    await self.handle_command(user_input)
                else:
                    await self.send_message(user_input)
            except KeyboardInterrupt:
                terminal_print("\nExiting JrDev terminal...", PrintType.INFO)
                self.running = False
            except Exception as e:
                terminal_print(f"Error: {str(e)}", PrintType.ERROR)


async def main(model=None):
    terminal = JrDevTerminal()
    if model and model in AVAILABLE_MODELS:
        terminal.model = model
    await terminal.run_terminal()


def run_cli():
    """Entry point for the command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JrDev Terminal - LLM model interface")
    parser.add_argument("--model", help="Specify the LLM model to use")
    parser.add_argument("--version", action="store_true", help="Show version information")
    
    args = parser.parse_args()
        
    if args.version:
        terminal_print("JrDev Terminal v0.1.0", PrintType.INFO)
        sys.exit(0)
        
    try:
        asyncio.run(main(args.model))
    except KeyboardInterrupt:
        terminal_print("\nExiting JrDev terminal...", PrintType.INFO)
        sys.exit(0)
