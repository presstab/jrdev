import asyncio
import json
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

from jrdev.agents import agent_tools
from jrdev.agents.router_agent import CommandInterpretationAgent
from jrdev.commands.keys import check_existing_keys, save_keys_to_env
from jrdev.core.clients import APIClients
from jrdev.core.commands import Command, CommandHandler
from jrdev.core.state import AppState
from jrdev.core.tool_call import ToolCall
from jrdev.core.user_settings import UserSettings
from jrdev.file_operations.file_utils import (JRDEV_DIR, JRDEV_PACKAGE_DIR,
                                              add_to_gitignore, get_env_path,
                                              get_persistent_storage_path,
                                              read_json_file, write_json_file,
                                              write_string_to_file)
from jrdev.logger import setup_logger
from jrdev.messages.thread import (  # Added MessageThread, THREADS_DIR
    THREADS_DIR, USER_INPUT_PREFIX, MessageThread)
from jrdev.models.api_provider import ApiProvider
from jrdev.models.model_list import ModelList
from jrdev.models.model_profiles import ModelProfileManager
from jrdev.models.model_utils import load_models, save_models
from jrdev.services.contextmanager import ContextManager
from jrdev.services.message_service import MessageService
from jrdev.ui.ui import PrintType
from jrdev.ui.ui_wrapper import UiWrapper
from jrdev.utils.treechart import generate_compact_tree
from jrdev.ui.tui.terminal_text_styles import TerminalTextStyles


class Application:
    def __init__(self, ui_mode="textual"):
        # Initialize core components
        self.logger = setup_logger(JRDEV_DIR)

        # Load persisted threads before AppState initialization
        persisted_threads = self._load_persisted_threads()

        self.state = AppState(persisted_threads=persisted_threads, ui_mode=ui_mode) # Pass loaded threads to AppState
        self.state.clients = APIClients()
        self.ui: UiWrapper = UiWrapper()

        # Add the router agent and its dedicated chat thread
        self.router_agent = None
        self.state.router_thread_id = self.state.create_thread(thread_id="", meta_data={"type": "router"})

        self.user_settings: UserSettings = UserSettings()
        self._load_user_settings()

        self.terminal_text_styles = TerminalTextStyles()

    def _load_user_settings(self) -> None:
        """Load user settings from disk"""
        file_path = get_persistent_storage_path() / "user_settings.json"
        try:
            data = read_json_file(str(file_path))
            if data and isinstance(data, Dict):
                max_router_iterations = data.get("max_router_iterations") # type: ignore
                if max_router_iterations:
                    self.user_settings.max_router_iterations = max_router_iterations
            else:
                self.logger.info("Creating user settings file %s", str(file_path))
                self.write_user_settings()
        except Exception:
            pass

    def write_user_settings(self) -> None:
        """Write user settings to disk"""
        file_path = get_persistent_storage_path() / "user_settings.json"
        settings = {"max_router_iterations": self.user_settings.max_router_iterations}
        if not write_json_file(str(file_path), settings):
            self.logger.error("Error writing user settings")

    def write_terminal_text_styles(self) -> None:
        """Write terminal text styles to disk"""
        if not self.terminal_text_styles.save_styles():
            self.logger.error("Error writing terminal text styles")

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

                    # Don't load old router threads
                    thread_type = thread.metadata.get("type")
                    if thread_type and thread_type == "router":
                        continue

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
        self.state.model_list.set_model_list(load_models())
        all_providers = self.state.clients.provider_list()
        provider_names = [provider.name for provider in all_providers]
        self.state.model_list.set_providers(provider_names)

        self.state.context_manager = ContextManager()

        # Instantiate ModelProfileManager
        profile_string_config_path = os.path.join(JRDEV_PACKAGE_DIR, "config", "profile_strings.json")
        self.state.model_profile_manager = ModelProfileManager(
            providers=all_providers,
            profile_strings_path=profile_string_config_path
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

    def _check_migration(self):
        """
        v1.0.0 and used jrdev as the dir name for JRDEV_DIR, v1.0.1 changes this to .jrdev dir
        Check for existence of old dir and prompt user to perform migration with /migrate command
        """
        # Check for old 'jrdev/' directory (not .jrdev/)
        old_dir = os.path.join(os.getcwd(), "jrdev")
        # Only prompt if old dir exists and new dir does not
        if os.path.isdir(old_dir):
            self.logger.warning("Old 'jrdev/' directory detected. Migration to new '.jrdev/' directory is required.")
            self.ui.print_text(
                "------------------\n|MIGRATION NEEDED|\n------------------\nDetected old 'jrdev/' directory. Please run '/migrate' to move your data to the new '.jrdev/' directory.",
                PrintType.WARNING
            )

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

        # Initialize the router agent
        self.router_agent = CommandInterpretationAgent(self)
        self.logger.info("CommandInterpretationAgent initialized.")

        self.logger.info("Application services initialized")
        return True

    def setup_complete(self):
        """This is run after UI is setup and can print welcome message etc"""
        # Perform the local context status check after basic setup/potential first-time run
        self._check_project_context_status()
        self._check_migration()

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

    def get_model_names(self) -> List[str]:
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

    def remove_model(self, model_name) -> bool:
        """Remove a model from runtime model list, flush to disk"""
        if not self.state.model_list.remove_model(model_name):
            return False

        save_models(self.state.model_list.get_model_list())
        self.ui.model_list_updated()
        return True

    def add_model(self, model_name: str, provider: str, is_think: bool, input_cost: int, output_cost: int, context_window: int) -> bool:
        """Add a model to runtime model list, flush to disk"""
        if not self.state.model_list.add_model(model_name, provider, is_think, input_cost, output_cost, context_window):
            return False

        save_models(self.state.model_list.get_model_list())
        self.ui.model_list_updated()
        return True

    def edit_model(self, model_name: str, provider: str, is_think: bool, input_cost: int, output_cost: int, context_window: int) -> bool:
        """Edit a model in the runtime model list and flush to disk"""
        if not self.state.model_list.update_model(model_name, provider, is_think, input_cost, output_cost, context_window):
            return False

        save_models(self.state.model_list.get_model_list())
        self.ui.model_list_updated()
        return True

    def refresh_model_list(self):
        # 1) grab every model from user's config (single source of truth)
        models = load_models()

        # 2) overwrite our in-memory list
        self.state.model_list.set_model_list(models)

        # 3) filter down to only providers we have keys for
        provider_names = [p.name for p in self.state.clients.provider_list()]
        self.state.model_list.set_providers(provider_names)

        # 4) notify listeners of models update
        self.ui.model_list_updated()

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
            # Invoke the CommandInterpretationAgent
            self.ui.print_text("Interpreting your request...\n", print_type=PrintType.PROCESSING)
            calls_made = []
            max_iter = self.user_settings.max_router_iterations
            i = 0
            while i < max_iter:
                i += 1
                tool_call: ToolCall = await self.router_agent.interpret(user_input, worker_id, calls_made)
                if not tool_call:
                    # Agent decided to clarify, chat, summarize, or failed. Stop processing.
                    break

                # The agent decided on a command, now execute it
                command_to_execute = tool_call.formatted_cmd
                self.ui.print_text(f"Running command: {command_to_execute}\nCommand Purpose: {tool_call.reasoning}\n", print_type=PrintType.PROCESSING)
                if tool_call.action_type == "command":
                    # commands print directly to console, therefore we have to capture console output for results
                    self.ui.start_capture()
                    command = Command(command_to_execute, worker_id)
                    await self.handle_command(command)
                    self.ui.end_capture()
                    tool_call.result = self.ui.get_capture()
                    # If the command was /code, we should break out of the router loop
                    # as /code is a self-contained agentic process.
                    if command_to_execute.startswith("/code"):
                        break
                elif tool_call.action_type == "tool":
                    try:
                        if tool_call.command not in agent_tools.tools_list:
                            tool_call.result = f"Error: Tool '{tool_call.command}' does not exist."
                        elif tool_call.command == "read_files":
                            tool_call.result = agent_tools.read_files(tool_call.args)
                        elif tool_call.command == "get_file_tree":
                            tool_call.result = agent_tools.get_file_tree()
                        elif tool_call.command == "write_file":
                            filename = tool_call.args[0]
                            content = " ".join(tool_call.args[1:])
                            tool_call.result = await agent_tools.write_file(self, filename, content)
                    except Exception as e:
                        error_message = f"Error executing tool '{tool_call.command}': {str(e)}"
                        self.logger.error(f"Tool execution failed: {error_message}", exc_info=True)
                        tool_call.result = error_message
                if not tool_call.has_next:
                    # This was the final command in the chain.
                    break

                # This was an info-gathering step, add result to history and loop again.
                calls_made.append(tool_call)
            if i >= max_iter:
                self.ui.print_text(
                    "My maximum command iterations have been hit for this request. Please reprompt to continue. You can"
                    " adjust this using the /routeragent command", print_type=PrintType.ERROR)

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
            if os.getenv(provider.env_key):
                providers_with_keys_names.append(provider.name)
        profile_manager = self.profile_manager()
        profile_manager.reload_if_using_fallback(providers_with_keys_names)

        self.state.need_first_time_setup = False
        return True

    def save_keys(self, keys):
        save_keys_to_env(keys)
        self.state.need_api_keys = not check_existing_keys(self)

    def provider_list(self) -> List[ApiProvider]:
        return self.state.clients.provider_list()

    async def reload_api_clients(self):
        self.state.clients.set_dirty()
        await self._initialize_api_clients()

    async def _initialize_api_clients(self):
        """Initialize all API clients"""
        # Create a dictionary of environment variables
        self.logger.info("initializing api clients")
        provider_env_keys = [provider.env_key for provider in self.state.clients.provider_list()]
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
