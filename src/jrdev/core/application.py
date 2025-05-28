import asyncio
import json
import os
import sys
from typing import Any, Dict, List
from dotenv import load_dotenv

from jrdev.core.clients import APIClients
from jrdev.core.commands import Command, CommandHandler
from jrdev.core.state import AppState
from jrdev.file_operations.file_utils import add_to_gitignore, JRDEV_DIR, JRDEV_PACKAGE_DIR, get_env_path
from jrdev.commands.keys import check_existing_keys, save_keys_to_env
from jrdev.logger import setup_logger
from jrdev.messages.thread import USER_INPUT_PREFIX, MessageThread, THREADS_DIR # Added MessageThread, THREADS_DIR
from jrdev.services.message_service import MessageService
from jrdev.models.model_list import ModelList
from jrdev.models.model_profiles import ModelProfileManager
from jrdev.models.model_utils import load_hardcoded_models
from jrdev.services.contextmanager import ContextManager
from jrdev.utils.treechart import generate_compact_tree
from jrdev.ui.ui import PrintType
from jrdev.ui.ui_wrapper import UiWrapper


class Application:
    def __init__(self, ui_mode="textual"):
        # Initialize core components
        self.logger = setup_logger(JRDEV_DIR)

        # Load persisted threads before AppState initialization
        persisted_threads = self._load_persisted_threads()

        self.state = AppState(persisted_threads=persisted_threads, ui_mode=ui_mode) # Pass loaded threads to AppState
        self.state.clients = APIClients()
        self.ui: UiWrapper = UiWrapper()

    def _load_persisted_threads(self) -> Dict[str, MessageThread]:
        """Load all persisted message threads from disk."""
        loaded_threads: Dict[str, MessageThread] = {}
        if not os.path.isdir(THREADS_DIR):
            self.logger.info(f"Threads directory '{THREADS_DIR}' not found. No threads to load.")
            return loaded_threads

        self.logger.info(f"Loading persisted threads from '{THREADS_DIR}'...")
        for filename in os.listdir(THREADS_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(THREADS_DIR, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if "thread_id" not in data:
                        self.logger.warning(f"File {file_path} is missing 'thread_id'. Skipping.")
                        continue

                    thread = MessageThread.from_dict(data)
                    loaded_threads[thread.thread_id] = thread
                    self.logger.debug(f"Successfully loaded thread: {thread.thread_id} from {file_path}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error decoding JSON from {file_path}: {e}. Skipping file.")
                except KeyError as e:
                    self.logger.error(f"Missing key in thread data from {file_path}: {e}. Skipping file.")
                except Exception as e:
                    self.logger.error(f"Unexpected error loading thread from {file_path}: {e}. Skipping file.")
        
        self.logger.info(f"Finished loading threads. Total loaded: {len(loaded_threads)}.")
        return loaded_threads

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
        profile_config_path = f"{JRDEV_PACKAGE_DIR}/config/profile_strings.json"
        
        # Determine active providers to inform ModelProfileManager's default profile selection
        all_providers = self.state.clients.provider_list()
        providers_with_keys_names = []
        for provider in all_providers:
            if os.getenv(provider["env_key"]):
                providers_with_keys_names.append(provider["name"])

        providers_path = f"{JRDEV_PACKAGE_DIR}/config/api_providers.json"

        self.state.model_profile_manager = ModelProfileManager(
            profile_strings_path=profile_config_path,
            providers_path=providers_path,
            active_provider_names=providers_with_keys_names
        )

    def _load_environment(self):
        """Load environment variables"""
        env_path = get_env_path()
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)

        if not check_existing_keys(self):
            self.state.need_first_time_setup = True
            self.state.need_api_keys = True
            self.ui.print_text("API keys not found. Setup will begin shortly...", PrintType.INFO)

    def _check_project_context_status(self):
        """
        Checks the status of the project context on startup and prints recommendations.
        This is a local check and does not involve LLM calls.
        """
        self.logger.info("Checking project context status...")
        try:
            # Ensure context manager is initialized
            if not hasattr(self.state, 'context_manager') or self.state.context_manager is None:
                self.logger.warning("ContextManager not initialized, skipping context status check.")
                # Check if the index file physically exists even if the manager isn't ready
                if not os.path.exists(os.path.join(JRDEV_DIR, "contexts", "file_index.json")):
                     self.ui.print_text(
                        "Project context not found. Run '/init' to analyze your project "
                        "for better AI understanding.",
                        PrintType.INFO
                    )
                return

            context_manager = self.state.context_manager
            index_path = context_manager.index_path

            # 1. Check if the index file exists
            if not os.path.exists(index_path) or len(context_manager.get_file_paths()) == 0:
                self.logger.info("Project context index file not found.")
                self.ui.print_text(
                    "Project context not found. Run '/init' to familiarize JrDev with important files the code.",
                    PrintType.INFO
                )
            else:
                # 2. Check for outdated files (this is the local check)
                outdated_files = context_manager.get_outdated_files()
                num_outdated = len(outdated_files)

                if num_outdated > 0:
                    self.logger.info(f"Found {num_outdated} outdated context files.")
                    self.ui.print_text(
                        f"Found {num_outdated} outdated project context file(s). "
                        f"Run '/projectcontext update' to refresh summaries for more "
                        f"accurate AI responses. To view outdate context file(s) run '/projectcontext status'",
                        PrintType.WARNING # Use WARNING to make it more noticeable
                    )
                else:
                    # Optional: Log that context is up-to-date
                    self.logger.info("Project context is up-to-date.")
                    # No message needed for the user if everything is okay.

        except Exception as e:
            # Log any unexpected errors during the check
            self.logger.error(f"Error checking project context status: {e}", exc_info=True)
            self.ui.print_text(
                "Could not verify project context status due to an internal error.",
                PrintType.ERROR
            )

    async def initialize_services(self):
        """Initialize API clients and services"""
        self.logger.info("initialize services")

        # First-time setup logic
        if hasattr(self.state, 'need_first_time_setup') and self.state.need_first_time_setup:
            success = await self._perform_first_time_setup()
            if not success:
                return False # Exit if setup failed or needs user action

        # API client initialization
        if not self.state.clients.is_initialized():
            self.logger.info("api clients not initialized")
            await self._initialize_api_clients()

        self.message_service = MessageService(self)

        self.logger.info("Application services initialized")
        return True

    def setup_complete(self):
        """This is run after UI is setup and can print welcome message etc"""
        # Perform the local context status check after basic setup/potential first-time run
        self._check_project_context_status()

    async def start_services(self):
        """Start background services"""
        # Start task monitor
        self.state.task_monitor = asyncio.create_task(self._schedule_task_monitor())
        self.logger.info("Background services started")

    async def handle_command(self, command: Command):
        cmd_parts = command.text.split()
        if not cmd_parts:
            return

        cmd = cmd_parts[0].lower()

        # Logging command
        self.logger.info(f"Command received: {cmd}")

        try:
            result = await self.command_handler.execute(cmd, cmd_parts, command.request_id)
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

    def get_thread(self, thread_id):
        """Get MessageThread instance"""
        return self.state.get_thread(thread_id)

    def get_all_threads(self):
        """Get all MessageThread instances"""
        return self.state.get_all_threads()

    def get_active_thread_id(self):
        return self.state.get_active_thread_id()

    def switch_thread(self, thread_id):
        """Switch to a different thread"""
        self.logger.info(f"Switching thread to {thread_id}")
        return self.state.switch_thread(thread_id)

    def create_thread(self, thread_id="") -> str:
        """Create a new thread"""
        return self.state.create_thread(thread_id)

    def stage_code_context(self, file_path) -> None:
        """Stage files that will be added as context to the next /code command"""
        self.state.stage_code_context(file_path)

    def remove_staged_code_context(self, file_path) -> bool:
        """Remove staged files"""
        return self.state.remove_staged_code_context(file_path)

    def get_code_context(self) -> List[str]:
        """Files that are staged for code command"""
        return list(self.state.get_code_context())

    def clear_code_context(self) -> None:
        """Clear staged code context"""
        self.state.clear_code_context()
        self.ui.code_context_update()

    async def send_message(self, msg_thread, content, writepath=None, print_stream=True, worker_id=None):
        """
        Send a message to the LLM with default behavior.
        If writepath is provided, the response will be saved to that file.
        """
        await self.message_service.send_message(msg_thread, content, writepath, print_stream, worker_id)

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
            # Persist the selected model to JRDEV_DIR/model_profiles.json
            config_path = os.path.join(JRDEV_DIR, "model_profiles.json")
            try:
                data = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        data = json.load(f)
                data['chat_model'] = model
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                self.logger.error(f"Error saving chat_model to config: {e}")
            if send_to_ui:
                self.ui.model_changed(model)

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

    def get_file_tree(self):
        current_dir = os.getcwd()
        return generate_compact_tree(current_dir, use_gitignore=True)

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

    async def process_input(self, user_input, worker_id=None):
        """Process user input."""
        await asyncio.sleep(0.01)  # Brief yield to event loop

        if not user_input:
            return

        if user_input.startswith("/"):
            command = Command(user_input, worker_id)
            result = await self.handle_command(command)
            # Check for special exit code
            if result == "EXIT":
                self.logger.info("Exit command received, forcing running state to False")
                self.state.running = False
        else:
            await self.process_chat_input(user_input, worker_id)

    async def process_chat_input(self, user_input, worker_id=None):
        # 1) get the active thread
        msg_thread = self.state.get_current_thread()
        thread_id = msg_thread.thread_id
        # 2) tell UI “I’m starting a new chat” (e.g. highlight the thread)
        self.ui.chat_thread_update(thread_id)
        # 3) stream the LLM response
        content = f"{USER_INPUT_PREFIX}{user_input}"
        async for chunk in self.message_service.stream_message(msg_thread, content, worker_id):
            # for each piece of text we hand it off to the UI
            self.ui.stream_chunk(thread_id, chunk)
        # 4) at the end, notify UI to refresh thread list or button state
        self.ui.chat_thread_update(thread_id)

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

        # redo model profiles if they are default
        all_providers = self.state.clients.provider_list()
        providers_with_keys_names = []
        for provider in all_providers:
            if os.getenv(provider["env_key"]):
                providers_with_keys_names.append(provider["name"])
        profile_manager = self.profile_manager()
        profile_manager.reload_if_using_fallback(providers_with_keys_names)

        self.state.need_first_time_setup = False
        return True

    def save_keys(self, keys):
        save_keys_to_env(keys)
        self.state.need_api_keys = not check_existing_keys(self)

    def provider_list(self):
        return self.state.clients.provider_list()

    async def reload_api_clients(self):
        self.state.clients.set_dirty()
        await self._initialize_api_clients()

    async def _initialize_api_clients(self):
        """Initialize all API clients"""
        # Create a dictionary of environment variables
        self.logger.info("initializing api clients")
        provider_env_keys = [provider["env_key"] for provider in self.state.clients.provider_list()]
        env = {key: os.getenv(key) for key in provider_env_keys}

        # Initialize all clients using the APIClients class
        try:
            await self.state.clients.initialize(env)
            self.logger.info("API clients initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize API clients: {str(e)}"
            self.logger.error(error_msg)
            self.ui.print_text(f"Error: {error_msg}", PrintType.ERROR)
            self.ui.print_text("Please restart the application and provide a valid API key.", PrintType.INFO)
            sys.exit(1)

    @property
    def context_manager(self):
        """Return the context manager for backward compatibility"""
        return self.state.context_manager if hasattr(self.state, 'context_manager') else None

    @property
    def context(self):
        """Return the context list for backward compatibility"""
        return self.state.context if hasattr(self.state, 'context') else []
