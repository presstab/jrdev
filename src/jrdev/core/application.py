import asyncio
import json
import os
import sys
from typing import Any, Dict, List
from dotenv import load_dotenv

from jrdev.colors import Colors
from jrdev.core.clients import APIClients
from jrdev.core.commands import CommandHandler
from jrdev.core.state import AppState
from jrdev.file_utils import add_to_gitignore, JRDEV_DIR, get_env_path
from jrdev.commands.keys import check_existing_keys, save_keys_to_env, run_first_time_setup
from jrdev.llm_requests import stream_request
from jrdev.logger import setup_logger
from jrdev.message_builder import MessageBuilder
from jrdev.model_list import ModelList
from jrdev.model_profiles import ModelProfileManager
from jrdev.model_utils import load_hardcoded_models
from jrdev.models import fetch_venice_models
from jrdev.ui.ui import PrintType
from jrdev.ui.ui_wrapper import UiWrapper
from jrdev.projectcontext.contextmanager import ContextManager


class Application:
    def __init__(self):
        # Initialize core components
        self.logger = setup_logger(JRDEV_DIR)
        self.state = AppState()
        self.state.clients = APIClients()
        self.ui: UiWrapper = UiWrapper()

    def setup(self):
        self._initialize_commands()
        self._setup_infrastructure()

    def _initialize_commands(self) -> None:
        """Initialize command handlers"""
        # Initialize the command handler
        self.command_handler = CommandHandler(self)

    def _setup_infrastructure(self):
        """Set up application infrastructure"""
        self._check_gitignore()
        self._load_environment()
        # Initialize state components
        self.state.model_list = ModelList()
        self.state.model_list.set_model_list(load_hardcoded_models())
        self.state.context_manager = ContextManager()
        self.state.model_profile_manager = ModelProfileManager()

    def _load_environment(self):
        """Load environment variables"""
        env_path = get_env_path()
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)

        if not check_existing_keys():
            self.state.need_first_time_setup = True
            self.state.need_api_keys = True
            self.ui.print_text("API keys not found. Setup will begin shortly...", PrintType.INFO)

    async def initialize_services(self):
        """Initialize API clients and services"""
        self.logger.info("initialize services")
        if hasattr(self.state, 'need_first_time_setup') and self.state.need_first_time_setup:
            success = await self._perform_first_time_setup()
            # UI signalled that keys or other steps need to be taken
            if not success:
                return False

        if not self.state.clients.is_initialized():
            self.logger.info("api clients not initialized")
            await self._initialize_api_clients()
            
        self.logger.info("Application services initialized")

        return True

    async def start_services(self):
        """Start background services"""
        # Start task monitor
        self.state.task_monitor = asyncio.create_task(self._schedule_task_monitor())
        
        # Start model update service
        model_update_task = asyncio.create_task(self._schedule_model_updates())
        
        self.logger.info("Background services started")

    async def handle_command(self, command):
        cmd_parts = command.split()
        if not cmd_parts:
            return

        cmd = cmd_parts[0].lower()

        # Logging command
        self.logger.info(f"Command received: {cmd}")

        try:
            result = await self.command_handler.execute(cmd, cmd_parts)
            return result
        except Exception as e:
            self.logger.error(f"Error handling command {cmd}: {e}")
            self.ui.print_text(f"Error: {e}", print_type=PrintType.ERROR)
            import traceback
            self.logger.error(traceback.format_exc())
            # Show help message for unknown commands
            if cmd not in self.command_handler.get_commands():
                self.ui.print_text("Type /help for available commands", print_type=PrintType.INFO)
        
    def get_current_thread(self):
        """Get the currently active thread"""
        return self.state.get_current_thread()
        
    def switch_thread(self, thread_id):
        """Switch to a different thread"""
        return self.state.switch_thread(thread_id)
        
    def create_thread(self, thread_id="") -> str:
        """Create a new thread"""
        return self.state.create_thread(thread_id)

    async def send_message(self, msg_thread, content, writepath=None, print_stream=True):
        """
        Send a message to the LLM with default behavior.
        If writepath is provided, the response will be saved to that file.

        Args:
            msg_thread: The message thread that this is being added to
            content: The message content to send
            writepath: Optional. If provided, the response will be saved to this path as a markdown file
            print_stream: Whether to print the stream response to terminal (default: True)

        Returns:
            str: The response text from the model
        """
        self.logger.info(f"Sending message to model {self.state.model}")

        if not isinstance(content, str):
            error_msg = f"Expected string but got {type(content)}"
            self.logger.error(error_msg)
            self.ui.print_text(f"Error: {error_msg}", PrintType.ERROR)
            return None

        user_additional_modifier = " Here is the user's question or instruction:"
        user_message = f"{user_additional_modifier} {content}"

        # Build actual request to send to LLM
        builder = MessageBuilder(self)
        builder.set_embedded_files(msg_thread.embedded_files)
        builder.start_user_section()

        # Update message history in the builder
        if msg_thread.messages:
            builder.add_historical_messages(msg_thread.messages)
        elif self.state.use_project_context:
            # only add project files on the first message in the thread
            builder.add_project_files()

        # Add user added context
        thread_context = msg_thread.context
        if thread_context:
            builder.add_context(list(thread_context))

        files_sent = builder.get_files()
        builder.append_to_user_section(user_message)
        builder.finalize_user_section()
        messages = builder.build()

        # update history on thread
        msg_thread.add_embedded_files(files_sent)
        msg_thread.messages = messages

        model_name = self.state.model
        self.ui.print_text(f"\n{model_name} is processing request in message thread: {msg_thread.thread_id}...", PrintType.PROCESSING)

        try:
            # Send the message to the LLM
            response_text = await stream_request(self, self.state.model, messages, print_stream=print_stream)
            self.logger.info(f"Successfully received response from model in thread {msg_thread.thread_id}")

            # Add response to messages
            msg_thread.add_response(response_text)

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
                    f.write(f"> Generated by {self.state.model} on {timestamp}\n\n")

                    # Write the LLM response
                    f.write(response_text)

                self.logger.info(f"Response saved to file: {writepath}")
                self.ui.print_text(f"Response saved to {writepath}", print_type=PrintType.SUCCESS)
                return response_text
            except Exception as e:
                error_msg = f"Error writing to file {writepath}: {str(e)}"
                self.logger.error(error_msg)
                self.ui.print_text(error_msg, print_type=PrintType.ERROR)
                return response_text
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error in send_message: {error_msg}")
            self.ui.print_text(f"Error: {error_msg}", PrintType.ERROR)
            return None
    
    def profile_manager(self):
        return self.state.model_profile_manager

    def get_models(self) -> List[Dict[str, Any]]:
        return self.state.model_list.get_model_list()

    def get_model_names(self):
        current_models = self.get_models()
        return [model["name"] for model in current_models]

    def set_model(self, model, send_to_ui=True):
        model_names = self.get_model_names()
        if model in model_names:
            self.state.model = model
            if send_to_ui:
                self.ui.model_changed(model)

    async def update_model_names_cache(self):
        """Update the model names cache in the background."""
        try:
            # Get current models from API
            models = await fetch_venice_models(client=self.state.clients.venice)

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
                    # Go up one directory to find jrdev/
                    parent_dir = os.path.dirname(current_dir)
                    json_path = os.path.join(parent_dir, "model_list.json")

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
                    self.state.model_list.append_model_list(venice_models)
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
        while self.state.running:
            try:
                # Update every hour
                await asyncio.sleep(3600)
                await self.update_model_names_cache()
            except Exception as e:
                self.logger.error(f"Error in model update task: {e}")
                # Wait a bit before retrying on error
                await asyncio.sleep(60)

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

    async def task_monitor_callback(self):
        """Periodic callback to check on background tasks and handle any completed ones."""
        try:
            # Check for completed or failed tasks that need cleanup
            completed_tasks = []
            for job_id, task_info in self.state.active_tasks.items():
                task = task_info.get("task")
                if task and task.done():
                    # Task is completed or failed, handle any cleanup if needed
                    if task.exception():
                        self.logger.error(f"Background task {job_id} failed with exception: {task.exception()}")
                    completed_tasks.append(job_id)

            # Remove completed tasks from active_tasks
            for job_id in completed_tasks:
                if job_id in self.state.active_tasks:
                    self.state.remove_task(job_id)
                    self.logger.info(f"Removed completed task {job_id} from active tasks")

            # Reschedule the monitor if terminal is still running
            if self.state.running:
                self.state.task_monitor = asyncio.create_task(self._schedule_task_monitor())
        except Exception as e:
            self.logger.error(f"Error in task monitor: {str(e)}")
            # Reschedule even if there was an error
            if self.state.running:
                self.state.task_monitor = asyncio.create_task(self._schedule_task_monitor())

    async def _schedule_task_monitor(self):
        """Schedule the task monitor to run after a delay."""
        await asyncio.sleep(1.0)  # Check every second
        await self.task_monitor_callback()

    async def process_input(self, user_input):
        """Process user input."""
        await asyncio.sleep(0.01)  # Brief yield to event loop
        
        if not user_input:
            return
            
        if user_input.startswith("/"):
            result = await self.handle_command(user_input)
            # Check for special exit code
            if result == "EXIT":
                self.logger.info("Exit command received, forcing running state to False")
                self.state.running = False
        else:
            msg_thread = self.state.get_current_thread()
            await self.send_message(msg_thread, user_input, print_stream=True)

    async def _perform_first_time_setup(self):
        """Handle first-time setup process"""
        self.logger.info("Performing first-time setup")
        if self.state.need_api_keys:
            await self.ui.signal_no_keys()
            return False

        if self.state.need_first_time_setup:
            self._load_environment()
            
        env_path = get_env_path()
        load_dotenv(dotenv_path=env_path)
        await self._initialize_api_clients()
        self.state.need_first_time_setup = False
        return True

    def save_keys(self, keys):
        save_keys_to_env(keys)
        self.state.need_api_keys = not check_existing_keys()

    async def _initialize_api_clients(self):
        """Initialize all API clients"""
        # Create a dictionary of environment variables
        self.logger.info("initializing api clients")
        env = {
            "VENICE_API_KEY": os.getenv("VENICE_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY")
        }
        
        # Initialize all clients using the APIClients class
        try:
            await self.state.clients.initialize(env)
            self.logger.info("API clients initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize API clients: {str(e)}"
            self.logger.error(error_msg)
            self.ui.print_text(f"Error: {error_msg}", PrintType.ERROR)
            self.ui.print_text("Please restart the application and provide a valid Venice API key.", PrintType.INFO)
            sys.exit(1)

    # Client property accessors for backward compatibility
    @property
    def venice_client(self):
        """Return the Venice client for backward compatibility"""
        return self.state.clients.venice if self.state.clients else None
        
    @property
    def openai_client(self):
        """Return the OpenAI client for backward compatibility"""
        return self.state.clients.openai if self.state.clients else None
        
    @property
    def anthropic_client(self):
        """Return the Anthropic client for backward compatibility"""
        return self.state.clients.anthropic if self.state.clients else None
        
    @property
    def deepseek_client(self):
        """Return the DeepSeek client for backward compatibility"""
        return self.state.clients.deepseek if self.state.clients else None
    
    @property
    def context_manager(self):
        """Return the context manager for backward compatibility"""
        return self.state.context_manager if hasattr(self.state, 'context_manager') else None
    
    @property
    def context(self):
        """Return the context list for backward compatibility"""
        return self.state.context if hasattr(self.state, 'context') else []
