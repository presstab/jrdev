#!/usr/bin/env python3

"""
Terminal interface for interacting with JrDev's LLM models
using OpenAI-compatible APIs.
"""
import asyncio
import sys
import platform

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
from jrdev.commands import (handle_clear, handle_cost, handle_exit, handle_help,
                                handle_init, handle_model, handle_models,
                                handle_stateinfo)
from jrdev.models import AVAILABLE_MODELS, is_think_model
from jrdev.llm_requests import stream_request
from jrdev.ui import terminal_print, PrintType
from jrdev.file_utils import *


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
            "/cost": handle_cost,
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
            files_to_send = requested_files(response_text)
            if files_to_send:

                terminal_print(f"\nDetected file request: {str(files_to_send)}", PrintType.INFO)
                files_content = get_file_contents(files_to_send)

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
            else:
                # do file changes here todo
                return
        except Exception as e:
            terminal_print(f"Error: {str(e)}", PrintType.ERROR)

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
