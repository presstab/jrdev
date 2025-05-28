import asyncio
import os
from jrdev.core.application import Application
from jrdev.ui.cli_events import CliEvents
from jrdev.ui.ui import PrintType
from jrdev.ui.colors import Colors
from jrdev import __version__


class CliApp:
    def __init__(self):
        self.core_app = Application(ui_mode="cli")
        self.ui = CliEvents(self.core_app)
        self.core_app.ui = self.ui
        self.setup_readline()

    async def run(self):
        """Main application entry point"""
        self.core_app.setup()
        await self.core_app.initialize_services()
        await self.core_app.start_services()
        await self._main_loop()

    async def _main_loop(self):
        """CLI Main application loop"""
        self._print_welcome_message()
        self.core_app.setup_complete()

        while self.core_app.state.running:
            try:
                user_input = await self.get_user_input()
                await self.core_app.process_input(user_input)
            except KeyboardInterrupt:
                self._handle_keyboard_interrupt()
            except Exception as e:
                self._handle_error(e)

        await self._shutdown_services()

    async def _shutdown_services(self):
        """Cleanup resources before exit"""
        if self.core_app.state.task_monitor and not self.core_app.state.task_monitor.done():
            self.core_app.state.task_monitor.cancel()
        self.core_app.logger.info("Application shutdown complete")

    def _handle_keyboard_interrupt(self):
        """Handle keyboard interrupt."""
        self.core_app.logger.info("User initiated terminal exit (KeyboardInterrupt)")
        self.ui.print_text("\nExiting JrDev terminal...", PrintType.INFO)
        self.core_app.state.running = False

    def _handle_error(self, error):
        """Handle general errors in main loop."""
        error_msg = str(error)
        self.logger.error(f"Error in main loop: {error_msg}")
        self.ui.print_text(f"Error: {error_msg}", PrintType.ERROR)

    def _print_welcome_message(self):
        """Print startup messages"""
        self.ui.print_text(f"JrDev Terminal v{__version__} (Model: {self.core_app.state.model})", PrintType.HEADER)
        self.ui.print_text("Type a message to chat with the model", PrintType.INFO)
        self.ui.print_text("Type /help for available commands", PrintType.INFO)
        self.ui.print_text("Type /exit to quit", PrintType.INFO)
        self.ui.print_text("Use /thread to manage conversation threads", PrintType.INFO)

    def setup_readline(self):
        """Set up the readline module for command history and tab completion."""
        try:
            import readline
            self.READLINE_AVAILABLE = True
        except ImportError:
            self.READLINE_AVAILABLE = False
            return

        try:
            self.history_file = os.path.expanduser("~/.jrdev_history")

            # Ensure the history file exists
            if not os.path.exists(self.history_file):
                try:
                    with open(self.history_file, 'w') as f:
                        pass  # Create empty file
                    self.core_app.logger.info(f"Created history file: {self.history_file}")
                except Exception as e:
                    self.core_app.logger.error(f"Failed to create history file: {e}")

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
            self.ui.print_text(f"Error setting up readline: {str(e)}", PrintType.ERROR)

    def completer(self, text, state):
        """
        Custom completer function for readline.
        Provides tab completion for commands and their arguments.
        """
        if not hasattr(self, 'READLINE_AVAILABLE') or not self.READLINE_AVAILABLE:
            return None

        try:
            import readline
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
                        model_names = self.core_app.get_model_names()
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
                        except Exception as e:
                            # Print debug info
                            print(f"\nError in file completion: {str(e)}")
                            return None

                    return None
                else:
                    # We're completing a command
                    matches = [cmd for cmd in self.core_app.command_handler.get_commands().keys() if cmd.startswith(line)]

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
        except Exception as e:
            self.core_app.logger.error(f"Error in completer: {e}")
            return None

        return None

    def save_history(self, input_text):
        """Save the input to history file."""
        if not hasattr(self, 'READLINE_AVAILABLE') or not self.READLINE_AVAILABLE or not input_text.strip():
            return

        try:
            import readline
            # Just write to history file
            # Don't add to in-memory history as input() already does this
            readline.write_history_file(self.history_file)
        except Exception as e:
            self.core_app.logger.error(f"Error saving history: {str(e)}")
            # Don't display errors to user as this isn't critical functionality

    async def get_user_input(self):
        """Get user input with proper line wrapping using asyncio to prevent blocking the event loop."""
        # We'll use a standard prompt and rely on Python's built-in input handling
        prompt = f"\n\001{Colors.BOLD}{Colors.GREEN}\002> \001{Colors.RESET}\002"

        # Use a clean approach to avoid history issues
        def read_input():
            if not hasattr(self, 'READLINE_AVAILABLE') or not self.READLINE_AVAILABLE:
                return input(prompt)

            import readline
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

            # Only work with readline if it's available
            if hasattr(self, 'READLINE_AVAILABLE') and self.READLINE_AVAILABLE:
                import readline

                # Readline will use this width for wrapping
                if hasattr(readline, 'set_screen_size'):
                    readline.set_screen_size(100, available_width)

                # Set up completion display hooks if available
                if hasattr(readline, 'set_completion_display_matches_hook'):
                    def hook(substitution, matches, longest_match_length):
                        print("\033[2K", end="")  # Clear line before showing matches
                    readline.set_completion_display_matches_hook(hook)

        except Exception as e:
            self.core_app.logger.error(f"Error setting up input dimensions: {str(e)}")

        # Use a less intrusive approach with asyncio to get input
        # This should help preserve readline's state better
        loop = asyncio.get_running_loop()
        user_input = await loop.run_in_executor(None, read_input)

        # Save to history if needed
        if user_input.strip():
            self.save_history(user_input)

        return user_input