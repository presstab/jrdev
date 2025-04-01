#!/usr/bin/env python3

"""
Main terminal interface for the JrDev CLI.
"""
import argparse
import asyncio
import json
import os
import platform
import re
import sys
from getpass import getpass

from dotenv import load_dotenv
from openai import AsyncOpenAI
from typing import Dict, List, Set
import anthropic  # Import Anthropic SDK

from jrdev.colors import Colors
from jrdev.commands import (handle_addcontext, handle_asyncsend, handle_cancel,
                            handle_clearcontext, handle_clearmessages, handle_code,
                            handle_cost, handle_exit, handle_git, handle_git_pr_summary, handle_help, 
                            handle_init, handle_keys, handle_model, handle_models,
                            handle_projectcontext, handle_stateinfo, handle_tasks,
                            handle_viewcontext)
from jrdev.file_utils import requested_files, get_file_contents, add_to_gitignore, JRDEV_DIR
from jrdev.commands.keys import check_existing_keys, run_first_time_setup
from jrdev.llm_requests import stream_request
# JrDev modules
from jrdev.logger import setup_logger
from jrdev.message_builder import MessageBuilder
from jrdev.model_list import ModelList
from jrdev.model_utils import load_hardcoded_models
from jrdev.models import fetch_venice_models
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.ui.ui import terminal_print, PrintType
from jrdev.projectcontext.contextmanager import ContextManager

# Cross-platform readline support
try:
    #if platform.system() == 'Windows':
    #    import pyreadline3 as readline
    #else:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False


class JrDevTerminal:
    def __init__(self):
        # Set up logging
        self.logger = setup_logger(JRDEV_DIR)
        self.logger.info("Initializing JrDevTerminal")

        # Check if jrdev/ is in gitignore and add it if not
        self._check_gitignore()

        # Try to load any existing .env file first
        if os.path.exists('.env'):
            load_dotenv()
            
        # Check for API keys and run first-time setup if needed
        if not check_existing_keys():
            # We need to run the async function from a synchronous context
            # Create a new event loop for just this call
            import asyncio
            loop = asyncio.new_event_loop()
            setup_success = False
            
            try:
                setup_success = loop.run_until_complete(run_first_time_setup())
            except Exception as e:
                self.logger.error(f"Error during first-time setup: {str(e)}")
                terminal_print(f"Error during setup: {str(e)}", PrintType.ERROR)
            finally:
                loop.close()
            
            # Check if setup was successful
            if not setup_success:
                terminal_print("Failed to set up required API keys. Exiting...", PrintType.ERROR)
                sys.exit(1)
                
            # Reload environment variables after setup
            load_dotenv()
        # If keys exist, we already loaded the .env file above

        # Initialize API clients
        self.venice_client = None
        self.openai_client = None
        self.anthropic_client = None
        self.deepseek_client = None

        # Get Venice API key - should be set now after setup
        venice_api_key = os.getenv("VENICE_API_KEY")
        if not venice_api_key:
            error_msg = "VENICE_API_KEY not found even after setup"
            self.logger.error(error_msg)
            terminal_print(f"Error: {error_msg}", PrintType.ERROR)
            terminal_print("Please restart the application and provide a valid Venice API key.", PrintType.INFO)
            sys.exit(1)

        # Initialize Venice client
        self.venice_client = AsyncOpenAI(
            api_key=venice_api_key,
            organization=None,
            project=None,
            base_url="https://api.venice.ai/api/v1",
        )

        # Get OpenAI API key (optional)
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.logger.info("OpenAI API key found, initializing OpenAI client")
            # Initialize OpenAI client
            self.openai_client = AsyncOpenAI(
                api_key=openai_api_key
            )
        else:
            self.logger.info("No OpenAI API key found, OpenAI models will not be available")
            
        # Get Anthropic API key (optional)
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            self.logger.info("Anthropic API key found, initializing Anthropic client")
            # Initialize Anthropic client - using AsyncAnthropic for async compatibility
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
        else:
            self.logger.info("No Anthropic API key found, Anthropic models will not be available")

        # Get DeepSeek API key (optional)
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_api_key:
            self.logger.info("DeepSeek API key found, initializing DeepSeek client")
            # Initialize OpenAI client
            self.deepseek_client = AsyncOpenAI(
                api_key=deepseek_api_key,
                organization=None,
                project=None,
                base_url="https://api.deepseek.com",
            )


        self.model = "deepseek-r1-671b"
        self.running = True
        self.messages = []
        self.files_in_history: Set[str] = set()

        # Thread safe list of models
        self.model_list = ModelList()

        # Project files dict to track various files used by the application
        self.project_files = {
            "filetree": f"{JRDEV_DIR}jrdev_filetree.txt",
            "overview": f"{JRDEV_DIR}jrdev_overview.md",
            "conventions": f"{JRDEV_DIR}jrdev_conventions.md"
        }

        # Context list to store additional context files for the LLM
        self.context = []

        # Use project overview, filetree, filecontext files in each request
        self.use_project_context = True

        # Initialize the context manager
        self.context_manager = ContextManager()
        
        # Track active background tasks
        self.active_tasks = {}

        # Background task monitor
        self.task_monitor = None

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
            "/addcontext": handle_addcontext,
            "/viewcontext": handle_viewcontext,
            "/asyncsend": handle_asyncsend,
            "/tasks": handle_tasks,
            "/cancel": handle_cancel,
            "/code": handle_code,
            "/projectcontext": handle_projectcontext,
            "/git": handle_git,
            "/keys": handle_keys
        }

        # Debug commands
        if os.getenv("JRDEV_DEBUG"):  # Only include in debug mode
            from jrdev.commands.debug import handle_modelswin
            self.command_handlers["/modelswin"] = handle_modelswin

        # Set up readline for command history
        self.history_file = os.path.expanduser("~/.jrdev_history")
        
        # Ensure the history file exists
        if not os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'w') as f:
                    pass  # Create empty file
                self.logger.info(f"Created history file: {self.history_file}")
            except Exception as e:
                self.logger.error(f"Failed to create history file: {e}")
        
        self.setup_readline()

        # setup initial models
        self.model_list.set_model_list(load_hardcoded_models())

    def get_models(self):
        return self.model_list.get_model_list()

    def get_model_names(self):
        current_models = self.get_models()
        return [model["name"] for model in current_models]

    async def update_model_names_cache(self):
        """Update the model names cache in the background."""
        try:
            # Get current models from API
            models = await fetch_venice_models(client=self.venice_client)

            if not models:
                self.logger.warning("Failed to fetch models from API")
                return

            # Get current models
            current_models = self.get_models()
            current_model_names = [model["name"] for model in current_models]

            # Find new models that aren't in the hardcoded list
            new_models = [model for model in models if model["name"] not in current_model_names]

            if new_models:
                # Print new models in a nice format
                self.logger.info("\nNew models discovered:")
                for model in new_models:
                    self.logger.info(f"  • {model['name']} ({model['provider']})")

                # Update model_list.json file with new models
                try:
                    # Get the directory where the module is located
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    json_path = os.path.join(current_dir, "model_list.json")

                    # Read the existing model list
                    with open(json_path, "r") as f:
                        model_list_data = json.load(f)

                    # Add new models to the list
                    for model in new_models:
                        # Create a model entry with default values
                        new_entry = {
                            "name": model["name"],
                            "provider": model["provider"],
                            "is_think": model["is_think"],
                            "input_cost": 0,  # Default to 0 for now
                            "output_cost": 0,  # Default to 0 for now
                            "context_tokens": model["context_tokens"]
                        }
                        model_list_data["models"].append(new_entry)

                    # Write the updated list back to the file
                    with open(json_path, "w") as f:
                        json.dump(model_list_data, f, indent=4)

                    self.logger.info(f"Updated model_list.json with {len(new_models)} new models")

                    # add new models
                    venice_models = [model for model in models if model["provider"] == "venice"]
                    self.model_list.append_model_list(venice_models)
                except Exception as e:
                    self.logger.error(f"Error updating model_list.json: {e}")
        except Exception as e:
            self.logger.error(f"Error updating model names cache: {e}")

    async def _schedule_model_updates(self):
        """Background task to periodically update model list."""
        try:
            # Perform an immediate update when the terminal starts
            await self.update_model_names_cache()
        except Exception as e:
            self.logger.error(f"Initial model update failed: {e}")

        # Then enter the periodic update loop
        while self.running:
            try:
                # Update every hour
                await asyncio.sleep(3600)
                await self.update_model_names_cache()
            except Exception as e:
                self.logger.error(f"Error in model update task: {e}")
                # Wait a bit before retrying on error
                await asyncio.sleep(60)

    async def handle_command(self, command):
        cmd_parts = command.split()
        if not cmd_parts:
            return

        cmd = cmd_parts[0].lower()

        # Logging command
        self.logger.info(f"Command received: {cmd}")

        if cmd in self.command_handlers:
            try:
                return await self.command_handlers[cmd](self, cmd_parts)
            except Exception as e:
                self.logger.error(f"Error handling command {cmd}: {e}")
                terminal_print(f"Error: {e}", print_type=PrintType.ERROR)
                import traceback
                self.logger.error(traceback.format_exc())
        else:
            self.logger.warning(f"Unknown command attempted: {cmd}")
            terminal_print(f"Unknown command: {cmd}", print_type=PrintType.ERROR)
            terminal_print("Type /help for available commands", print_type=PrintType.INFO)

    def set_message_history(self, messages, files):
        self.messages = messages
        self.files_in_history = files

    def add_message_history(self, text, is_assistant=False):
        self.messages.append({"role": "assistant" if is_assistant else "user", "content": text})

    def message_history(self):
        return self.messages

    def clear_messages(self):
        self.messages.clear()

    async def send_message(self, content, writepath=None, print_stream=True):
        """
        Send a message to the LLM with default behavior.
        If writepath is provided, the response will be saved to that file.

        Args:
            content: The message content to send
            writepath: Optional. If provided, the response will be saved to this path as a markdown file
            print_stream: Whether to print the stream response to terminal (default: True)

        Returns:
            str: The response text from the model
        """
        self.logger.info(f"Sending message to model {self.model}")

        if not isinstance(content, str):
            error_msg = f"Expected string but got {type(content)}"
            self.logger.error(error_msg)
            terminal_print(f"Error: {error_msg}", PrintType.ERROR)
            return None

        user_additional_modifier = " Here is the user's question or instruction:"
        user_message = f"{user_additional_modifier} {content}"

        # Build actual request to send to LLM
        builder = MessageBuilder(self)
        builder.set_embedded_files(self.files_in_history)
        builder.start_user_section()

        # Update message history in the builder
        if self.message_history():
            builder.add_historical_messages(self.message_history())
        elif self.use_project_context:
            # only add project files on the first message in the thread
            builder.add_project_files()

        # Add user added context
        if self.context:
            builder.add_context(self.context)

        files_sent = builder.get_files()
        builder.append_to_user_section(user_message)
        builder.finalize_user_section()
        messages = builder.build()

        # reset history to the current chain
        self.set_message_history(messages, files_sent)

        model_name = self.model
        terminal_print(f"\n{model_name} is processing request...", PrintType.PROCESSING)

        try:
            # Pass the print_stream parameter to control whether to print the model's response
            response_text = await stream_request(self, self.model, messages, print_stream)
            self.logger.info("Successfully received response from model")

            # Add response to messages
            self.add_message_history(response_text, is_assistant=True)

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

                self.logger.info(f"Response saved to file: {writepath}")
                terminal_print(f"Response saved to {writepath}", print_type=PrintType.SUCCESS)
                return response_text
            except Exception as e:
                error_msg = f"Error writing to file {writepath}: {str(e)}"
                self.logger.error(error_msg)
                terminal_print(error_msg, print_type=PrintType.ERROR)
                return response_text
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error in send_message: {error_msg}")
            terminal_print(f"Error: {error_msg}", PrintType.ERROR)
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
                    model_names = [model["name"] for model in self.get_model_names()]
                    matches = [name for name in model_names if name.startswith(args_prefix)]

                    # If there's only one match and we've pressed tab once (state == 0)
                    if len(matches) == 1 and state == 0:
                        return matches[0]

                    # If there are multiple matches and this is the first time showing them (state == 0)
                    if len(matches) > 1 and state == 0:
                        # Print a newline to start the completions on a fresh line
                        print("\033[2K\n")

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
                                print("\033[2K\n")

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
                    print("\033[2K\n")

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

    def _check_gitignore(self):
        """
        Check if JRDEV_DIR is in the .gitignore file and add it if not.
        This helps ensure that jrdev generated files don't get committed to git.
        """
        try:
            gitignore_path = ".gitignore"

            # Check if the gitignore pattern exists and add if it doesn't
            gitignore_pattern = f"{JRDEV_DIR}*"

            # Add the pattern to gitignore
            # The add_to_gitignore function already checks if the pattern exists
            result = add_to_gitignore(gitignore_path, gitignore_pattern)

            self.logger.info(f"Gitignore check completed: {'pattern added' if result else 'pattern already exists'}")
        except Exception as e:
            self.logger.error(f"Error checking gitignore: {str(e)}")

    def setup_readline(self):
        """Set up the readline module for command history and tab completion."""
        if not READLINE_AVAILABLE:
            return

        try:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(self.completer)
            readline.set_completer_delims(' \t\n;')

            # Make sure readline's history length is set properly
            readline.set_history_length(1000)

            # Initial history load
            if os.path.exists(self.history_file):
                readline.read_history_file(self.history_file)
            
            # Refresh display if needed
            if hasattr(readline, 'redisplay'):
                readline.redisplay()

            if hasattr(readline, 'set_screen_size'):
                try:
                    import shutil
                    columns, _ = shutil.get_terminal_size()
                    readline.set_screen_size(100, columns)
                except Exception:
                    readline.set_screen_size(100, 120)
        except Exception as e:
            terminal_print(f"Error setting up readline: {str(e)}", PrintType.ERROR)

    def save_history(self, input_text):
        """Save the input to history file."""
        if not READLINE_AVAILABLE or not input_text.strip():
            return

        try:
            # Just write to history file
            # Don't add to in-memory history as input() already does this
            readline.write_history_file(self.history_file)
        except Exception as e:
            self.logger.error(f"Error saving history: {str(e)}")
            # Don't display errors to user as this isn't critical functionality

    async def get_user_input(self):
        """Get user input with proper line wrapping using asyncio to prevent blocking the event loop."""
        # We'll use a standard prompt and rely on Python's built-in input handling
        prompt = f"\n\001{Colors.BOLD}{Colors.GREEN}\002> \001{Colors.RESET}\002"

        # Use a clean approach to avoid history issues
        def read_input():
            if not READLINE_AVAILABLE:
                return input(prompt)

            # Refresh display to ensure proper cursor state
            if hasattr(readline, 'redisplay'):
                readline.redisplay()
                
            # Use the standard input with proper prompt
            try:
                # Use the standard prompt-with-input approach
                # The readline library will properly handle the prompt protection
                return input(prompt)
            except KeyboardInterrupt:
                print("\n")
                return ""
            except EOFError:
                readline.clear_history()  # Add history cleanup on EOF
                print("\n")
                return ""

        try:
            # Get terminal width to help with wrapping behavior
            import shutil
            term_width = shutil.get_terminal_size().columns
            # Adjust prompt width consideration
            prompt_len = 4  # Length of "> " without color codes
            available_width = term_width - prompt_len

            # Readline will use this width for wrapping
            if READLINE_AVAILABLE and hasattr(readline, 'set_screen_size'):
                readline.set_screen_size(100, available_width)
                
            # Set up completion display hooks if available
            if READLINE_AVAILABLE and hasattr(readline, 'set_completion_display_matches_hook'):
                def hook(substitution, matches, longest_match_length):
                    print("\033[2K", end="")  # Clear line before showing matches
                readline.set_completion_display_matches_hook(hook)

        except Exception as e:
            self.logger.error(f"Error setting up input dimensions: {str(e)}")

        # Use a less intrusive approach with asyncio to get input
        # This should help preserve readline's state better
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, read_input)

    async def task_monitor_callback(self):
        """Periodic callback to check on background tasks and handle any completed ones."""
        try:
            # Check for completed or failed tasks that need cleanup
            completed_tasks = []
            for job_id, task_info in self.active_tasks.items():
                task = task_info.get("task")
                if task and task.done():
                    # Task is completed or failed, handle any cleanup if needed
                    if task.exception():
                        self.logger.error(f"Background task {job_id} failed with exception: {task.exception()}")
                    completed_tasks.append(job_id)

            # Remove completed tasks from active_tasks
            for job_id in completed_tasks:
                if job_id in self.active_tasks:
                    del self.active_tasks[job_id]
                    self.logger.info(f"Removed completed task {job_id} from active tasks")

            # Reschedule the monitor if terminal is still running
            if self.running:
                self.task_monitor = asyncio.create_task(self._schedule_task_monitor())
        except Exception as e:
            self.logger.error(f"Error in task monitor: {str(e)}")
            # Reschedule even if there was an error
            if self.running:
                self.task_monitor = asyncio.create_task(self._schedule_task_monitor())

    async def _schedule_task_monitor(self):
        """Schedule the task monitor to run after a delay."""
        await asyncio.sleep(1.0)  # Check every second
        await self.task_monitor_callback()

    async def run_terminal(self):
        self.logger.info(f"JrDev Terminal started with model: {self.model}")
        terminal_print(f"JrDev Terminal (Model: {self.model})", PrintType.HEADER)
        terminal_print("Type a message to chat with the model", PrintType.INFO)
        terminal_print("Type /help for available commands", PrintType.INFO)
        terminal_print("Type /exit to quit", PrintType.INFO)
        if READLINE_AVAILABLE:
            terminal_print("Use up/down arrows to navigate command history", PrintType.INFO)

        # Start the task monitor
        self.task_monitor = asyncio.create_task(self._schedule_task_monitor())
        self.logger.info("Task monitor started")

        # Start the model update task
        model_update_task = asyncio.create_task(self._schedule_model_updates())
        self.logger.info("Model update task started")

        while self.running:
            try:
                # Get user input asynchronously, allowing background tasks to run
                # With our new implementation, this will handle history properly
                user_input = await self.get_user_input()

                # Brief yield to the event loop to allow background tasks to progress
                await asyncio.sleep(0.01)

                # We no longer need to explicitly add to history since input() handles it
                # Just save to history file if it's not empty
                if user_input.strip():
                    self.save_history(user_input)

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    await self.handle_command(user_input)
                else:
                    # Send the message and print the streamed response from the model
                    # No need to use the return value since stream_request already
                    # handles printing the model's response to the terminal
                    await self.send_message(user_input, print_stream=True)
            except KeyboardInterrupt:
                self.logger.info("User initiated terminal exit (KeyboardInterrupt)")
                terminal_print("\nExiting JrDev terminal...", PrintType.INFO)
                self.running = False
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error in run_terminal: {error_msg}")
                terminal_print(f"Error: {error_msg}", PrintType.ERROR)

        # Cancel the task monitor when shutting down
        if self.task_monitor and not self.task_monitor.done():
            self.task_monitor.cancel()
            self.logger.info("Task monitor cancelled")

        self.logger.info("JrDev Terminal gracefully shut down")


async def main(model=None):
    terminal = JrDevTerminal()
    if model:
        model_names = [m["name"] for m in terminal.get_model_names()]
        if model in model_names:
            terminal.model = model
    await terminal.run_terminal()


def run_cli():
    """Entry point for the command-line interface."""

    parser = argparse.ArgumentParser(description="JrDev Terminal - LLM model interface")
    parser.add_argument("--version", action="store_true", help="Show version information")

    args = parser.parse_args()

    if args.version:
        terminal_print("JrDev Terminal v0.1.0", PrintType.INFO)
        sys.exit(0)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        terminal_print("\nExiting JrDev terminal...", PrintType.INFO)
        sys.exit(0)
