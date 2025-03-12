#!/usr/bin/env python3
"""
Terminal interface for interacting with JrDev's LLM models
using OpenAI-compatible APIs.
"""

import asyncio
import sys
import platform
import os
import re

from openai import AsyncOpenAI

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
from jrdev.commands import (handle_addcontext, handle_asyncsend, handle_cancel,
                            handle_clearcontext, handle_clearmessages, handle_cost, 
                            handle_exit, handle_help, handle_init, handle_model, 
                            handle_models, handle_process, handle_stateinfo, 
                            handle_tasks, handle_viewcontext)
from jrdev.models import AVAILABLE_MODELS, is_think_model
from jrdev.llm_requests import stream_request
from jrdev.ui import terminal_print, PrintType
from jrdev.file_utils import requested_files, get_file_contents, check_and_apply_code_changes


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
        
        # Project files dict to track various files used by the application
        self.project_files = {
            "filetree": "jrdev_filetree.txt",
            "filecontext": "jrdev_filecontext.md",
            "overview": "jrdev_overview.md",
            "code_change_example": "code_change_example.json"
        }
        
        # Context list to store additional context files for the LLM
        self.context = []
        
        # Controls whether to process file requests and code changes
        self.process_follow_up = False
        
        # Track active background tasks
        self.active_tasks = {}

        # Initialize command handlers dictionary
        self.command_handlers = {
            "/exit": handle_exit,
            "/model": handle_model,
            "/models": handle_models,
            "/stateinfo": handle_stateinfo,
            "/clearcontext": handle_clearcontext,
            "/clearmessages": handle_clearmessages,
            "/cost": handle_cost,
            "/init": handle_init,
            "/help": handle_help,
            "/process": handle_process,
            "/addcontext": handle_addcontext,
            "/viewcontext": handle_viewcontext,
            "/asyncsend": handle_asyncsend,
            "/tasks": handle_tasks,
            "/cancel": handle_cancel,
        }
        
        # Set up readline for command history
        self.history_file = os.path.expanduser("~/.jrdev_history")
        self.setup_readline()

    async def handle_command(self, command):
        cmd_parts = command.split()
        if not cmd_parts:
            return

        cmd = cmd_parts[0].lower()

        if cmd in self.command_handlers:
            return await self.command_handlers[cmd](self, cmd_parts)
        else:
            terminal_print(f"Unknown command: {cmd}", PrintType.ERROR)
            terminal_print("Type /help for available commands", PrintType.INFO)

    async def send_simple_message(self, content, process_follow_up=False):
        """
        Send a message to the LLM without processing follow-up tasks like file requests
        and code changes unless explicitly requested.

        Args:
            content: The message content to send
            process_follow_up: Whether to process follow-up tasks like file requests and code changes
        
        Returns:
            str: The response text from the model
        """
        if not isinstance(content, str):
            terminal_print(f"Error: expected string but got {type(content)}", PrintType.ERROR)
            return None
            
        # Read project context files if they exist
        project_context = {}
        for key, filename in self.project_files.items():
            try:
                if os.path.exists(filename):
                    with open(filename, "r") as f:
                        project_context[key] = f.read()
            except Exception as e:
                terminal_print(f"Warning: Could not read {filename}: {str(e)}", PrintType.WARNING)

        # Build the complete message
        dev_prompt_modifier = (
            "You are an expert software architect and engineer reviewing an attached project. An engineer from the project is asking for guidance on how to complete a specific task. Begin by providing a high-level analysis of the task, outlining the necessary steps and strategy without including any code changes. "
            "**CRITICAL:** Do not propose any code modifications until you have received and reviewed the full content of the relevant file(s). If the file content is not yet in your context, request it using the exact format: "
            "'get_files [\"path/to/file1.txt\", \"path/to/file2.cpp\", ...]'. Only after the complete file content is available should you suggest code changes."
        )
        dev_prompt_modifier = None

        user_additional_modifier = " Here is the user's question or instruction:"
        user_message = f"{user_additional_modifier} {content}"

        if self.model not in self.messages:
            self.messages[self.model] = []

            # Append project context if available (only needed on first run)
            if project_context:
                for key, value in project_context.items():
                    user_message = f"{user_message}\n\n{key.upper()}:\n{value}"
            if dev_prompt_modifier is not None:
                self.messages[self.model].append({"role": "system", "content": dev_prompt_modifier})
        
        # Add any additional context files stored in self.context
        if self.context:
            context_section = "\n\nUSER CONTEXT:\n"
            for i, ctx in enumerate(self.context):
                context_section += f"\n--- Context File {i+1}: {ctx['name']} ---\n{ctx['content']}\n"
            user_message += context_section

        self.messages[self.model].append({"role": "user", "content": user_message})

        model_name = self.model
        terminal_print(f"\n{model_name} is processing request...", PrintType.PROCESSING)

        try:
            response_text = await stream_request(self.client, self.model, self.messages[self.model])
            # Add a new line after streaming completes
            terminal_print("", PrintType.INFO)
            
            # Always add response to messages
            self.messages[self.model].append({"role": "assistant", "content": response_text})
            
            # Only process follow-up tasks if explicitly requested
            if process_follow_up:
                # Process file requests if present
                files_to_send = requested_files(response_text)
                if files_to_send:
                    terminal_print(f"\nDetected file request: {files_to_send}", PrintType.INFO)
                    files_content = get_file_contents(files_to_send)
                    dev_msg = (
                    """
                    If code modifications are needed, return a JSON object with a 'files' key containing a full rewrite of the
                    file which includes the recommended changes, no additional explanation is needed since this will only be visible to machines:
                    {
                        "files": [
                            {
                                "filename": "example.py",
                                "path": "src/util/",
                                "content": "full file goes in here. use new line\n for line changing\n"
                            },
                            {file2 content....}
                        ]
                    }
                    """)

                    follow_up_message = (f"As you rewrite this code, leave the code as unchanged as possible, except for the areas"
                                         f" where code changes are needed to complete the task. For example, leave all comments and don't"
                                         f" 'clean up' the code. These requested files will give you the needed context to make changes to the code:{files_content}")
                    self.messages[self.model].append({"role": "user", "content": follow_up_message})
                    self.messages[self.model].append({"role": "system", "content": dev_msg})

                    terminal_print(f"\nSending requested files to {model_name}...", PrintType.PROCESSING)
                    follow_up_response = await stream_request(self.client, self.model, self.messages[self.model])
                    terminal_print("", PrintType.INFO)
                    self.messages[self.model].append({"role": "assistant", "content": follow_up_response})
                    # Process code changes from the follow-up response
                    check_and_apply_code_changes(follow_up_response)
                else:
                    # If no file request, check the original response for code changes
                    check_and_apply_code_changes(response_text)
            
            return response_text
        except Exception as e:
            terminal_print(f"Error: {str(e)}", PrintType.ERROR)
            return None
    
    async def send_message(self, content, writepath=None):
        """
        Send a message to the LLM with default behavior.
        If writepath is provided, the response will be saved to that file.
        
        Args:
            content: The message content to send
            writepath: Optional. If provided, the response will be saved to this path as a markdown file
        
        Returns:
            str: The response text from the model
        """
        if not isinstance(content, str):
            terminal_print(f"Error: expected string but got {type(content)}", PrintType.ERROR)
            return None

        # Read project context files if they exist
        project_context = {}
        for key, filename in self.project_files.items():
            try:
                if os.path.exists(filename):
                    with open(filename, "r") as f:
                        project_context[key] = f.read()
            except Exception as e:
                terminal_print(f"Warning: Could not read {filename}: {str(e)}", PrintType.WARNING)

        user_additional_modifier = " Here is the user's question or instruction:"
        user_message = f"{user_additional_modifier} {content}"

        # Append project context if available (only needed on first run)
        if project_context:
            for key, value in project_context.items():
                user_message = f"{user_message}\n\n{key.upper()}:\n{value}"

        # Add any additional context files stored in self.context
        if self.context:
            context_section = "\n\nUSER CONTEXT:\n"
            for i, ctx in enumerate(self.context):
                context_section += f"\n--- Context File {i + 1}: {ctx['name']} ---\n{ctx['content']}\n"
            user_message += context_section

        messages = []
        messages.append({"role": "user", "content": user_message})

        model_name = self.model
        terminal_print(f"\n{model_name} is processing request...", PrintType.PROCESSING)

        try:
            response_text = await stream_request(self.client, self.model, self.messages[self.model])
            
            # Add response to messages
            self.messages[self.model].append({"role": "assistant", "content": response_text})
            
            if writepath is None:
                return response_text
                
            # Make sure the writepath has .md extension
            if not writepath.endswith('.md'):
                writepath = f"{writepath}.md"
                
            # Create directory structure if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(writepath)), exist_ok=True)
            
            # Write the response to the specified file path
            try:
                with open(writepath, 'w') as f:
                    # Add a title based on the file name
                    title = os.path.basename(writepath).replace('.md', '').replace('_', ' ').title()
                    f.write(f"# {title}\n\n")
                    
                    # Write timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"> Generated by {self.model} on {timestamp}\n\n")
                    
                    # Write the LLM response
                    f.write(response_text)
                
                terminal_print(f"Response saved to {writepath}", print_type=PrintType.SUCCESS)
                return response_text
            except Exception as e:
                terminal_print(f"Error writing to file {writepath}: {str(e)}", print_type=PrintType.ERROR)
                return response_text
        except Exception as e:
            terminal_print(f"Error: {str(e)}", PrintType.ERROR)
            return None

    def is_inside_think_tag(self, text):
        """Determine if the current position is inside a <think> tag."""
        think_open = text.count("<think>")
        think_close = text.count("</think>")
        return think_open > think_close

    def filter_think_tags(self, text):
        """Remove content within <think></think> tags."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    def completer(self, text, state):
        """
        Custom completer function for readline.
        Provides tab completion for commands and their arguments.
        """
        buffer = readline.get_line_buffer()
        line = buffer.lstrip()
        
        # If the line starts with a slash, it might be a command
        if line.startswith("/"):
            
            # Check if we're completing a command or its arguments
            if " " in line:
                # We're completing arguments for a command
                command, args_prefix = line.split(" ", 1)
                
                # If the command is /model, provide model name completions
                if command == "/model":
                    model_names = [model["name"] for model in AVAILABLE_MODELS]
                    matches = [name for name in model_names if name.startswith(args_prefix)]
                    
                    # If there's only one match and we've pressed tab once (state == 0)
                    if len(matches) == 1 and state == 0:
                        return matches[0]
                    
                    # If there are multiple matches and this is the first time showing them (state == 0)
                    if len(matches) > 1 and state == 0:
                        # Print a newline to start the completions on a fresh line
                        print("\n")
                        
                        # Print all matches in columns 
                        terminal_width = os.get_terminal_size().columns
                        max_item_len = max(len(item) for item in matches) + 2  # +2 for spacing
                        items_per_row = max(1, terminal_width // max_item_len)
                        
                        for i, item in enumerate(matches):
                            print(f"{item:<{max_item_len}}", end=("" if (i + 1) % items_per_row else "\n"))
                        
                        # If we didn't end with a newline, print one now
                        if len(matches) % items_per_row != 0:
                            print()
                        
                        # Redisplay the prompt and current input
                        print(f"\n{Colors.BOLD}{Colors.GREEN}> {Colors.RESET}{command} {args_prefix}", end="", flush=True)
                    
                    # Return items based on state
                    try:
                        return matches[state]
                    except IndexError:
                        return None
                
                # If the command is /addcontext, provide file path completions
                elif command == "/addcontext":
                    # Get the current working directory
                    cwd = os.getcwd()
                    
                    # Check if args_prefix contains wildcard (*, ?, [)
                    has_wildcard = any(c in args_prefix for c in ['*', '?', '['])
                    
                    # If it has a wildcard already, we don't provide completions
                    if has_wildcard:
                        return None
                    
                    # Split the args_prefix into directory and filename parts
                    if "/" in args_prefix:
                        dir_prefix, file_prefix = os.path.split(args_prefix)
                        dir_path = os.path.join(cwd, dir_prefix)
                    else:
                        dir_path = cwd
                        file_prefix = args_prefix
                    
                    try:
                        # Get all files and directories in the target directory
                        if os.path.isdir(dir_path):
                            items = os.listdir(dir_path)
                            matches = []
                            
                            for item in items:
                                # Only include items that match the prefix
                                if item.startswith(file_prefix):
                                    full_item = item
                                    # If the args_prefix includes a directory, include it in the completion
                                    if "/" in args_prefix:
                                        full_item = os.path.join(dir_prefix, item)
                                    
                                    # Add a trailing slash for directories
                                    full_path = os.path.join(cwd, dir_prefix if "/" in args_prefix else "", item)
                                    if os.path.isdir(full_path):
                                        full_item += "/"
                                    
                                    matches.append(full_item)
                            
                            # If there's only one match and we've pressed tab once (state == 0)
                            if len(matches) == 1 and state == 0:
                                return matches[0]
                            
                            # If there are multiple matches and this is the first time showing them (state == 0)
                            if len(matches) > 1 and state == 0:
                                # Print a newline to start the completions on a fresh line
                                print("\n")
                                
                                # Print all matches in columns (we could get fancy with column formatting, but keeping it simple)
                                terminal_width = os.get_terminal_size().columns
                                max_item_len = max(len(item) for item in matches) + 2  # +2 for spacing
                                items_per_row = max(1, terminal_width // max_item_len)
                                
                                for i, item in enumerate(matches):
                                    print(f"{item:<{max_item_len}}", end=("" if (i + 1) % items_per_row else "\n"))
                                
                                # If we didn't end with a newline, print one now
                                if len(matches) % items_per_row != 0:
                                    print()
                                
                                # Redisplay the prompt and current input
                                print(f"\n{Colors.BOLD}{Colors.GREEN}> {Colors.RESET}{command} {args_prefix}", end="", flush=True)
                                
                            # Return items based on state
                            try:
                                return matches[state]
                            except IndexError:
                                return None
                    except Exception as e:
                        # Print debug info
                        print(f"\nError in file completion: {str(e)}")
                        return None
                
                return None
            else:
                # We're completing a command
                matches = [cmd for cmd in self.command_handlers.keys() if cmd.startswith(line)]
                
                # If there's only one match and we've pressed tab once (state == 0)
                if len(matches) == 1 and state == 0:
                    return matches[0]
                
                # If there are multiple matches and this is the first time showing them (state == 0)
                if len(matches) > 1 and state == 0:
                    # Print a newline to start the completions on a fresh line
                    print("\n")
                    
                    # Print all matches in columns 
                    terminal_width = os.get_terminal_size().columns
                    max_item_len = max(len(item) for item in matches) + 2  # +2 for spacing
                    items_per_row = max(1, terminal_width // max_item_len)
                    
                    for i, item in enumerate(matches):
                        print(f"{item:<{max_item_len}}", end=("" if (i + 1) % items_per_row else "\n"))
                    
                    # If we didn't end with a newline, print one now
                    if len(matches) % items_per_row != 0:
                        print()
                    
                    # Redisplay the prompt and current input
                    print(f"\n{Colors.BOLD}{Colors.GREEN}> {Colors.RESET}{line}", end="", flush=True)
                
                # Return items based on state
                try:
                    return matches[state]
                except IndexError:
                    return None
        
        return None

    def setup_readline(self):
        """Set up the readline module for command history and tab completion."""
        if not READLINE_AVAILABLE:
            return

        try:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(self.completer)
            readline.set_completer_delims(' \t\n;')
            if hasattr(readline, 'set_screen_size'):
                try:
                    import shutil
                    columns, _ = shutil.get_terminal_size()
                    readline.set_screen_size(100, columns)
                except Exception:
                    readline.set_screen_size(100, 120)
            if os.path.exists(self.history_file):
                readline.read_history_file(self.history_file)
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
    if model:
        model_names = [m["name"] for m in AVAILABLE_MODELS]
        if model in model_names:
            terminal.model = model
    await terminal.run_terminal()


def run_cli():
    """Entry point for the command-line interface."""
    import argparse
    
    # Get list of available model names for argparse choices
    model_names = [model["name"] for model in AVAILABLE_MODELS]
    
    parser = argparse.ArgumentParser(description="JrDev Terminal - LLM model interface")
    parser.add_argument("--model", help="Specify the LLM model to use", choices=model_names)
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
