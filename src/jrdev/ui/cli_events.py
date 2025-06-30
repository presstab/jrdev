from jrdev.ui.ui import terminal_print, PrintType
from jrdev.ui.ui_wrapper import UiWrapper
from jrdev.commands.keys import check_existing_keys, run_first_time_setup
from typing import Any, List, Optional, Tuple
import sys
import json
from jrdev.ui.cli.curses_editor import is_curses_available, edit_text

class CliEvents(UiWrapper):
    def __init__(self, app):  # Add app reference
        super().__init__()
        self.ui_name = "cli"
        self.app = app

    def print_text(self, message: Any, print_type: PrintType = PrintType.INFO, end: str = "\n", prefix: Optional[str] = None, flush: bool = False):
        # Post custom message when print is called
        terminal_print(message, print_type, end, prefix, flush)

    def print_stream(self, message: str):
        """print a stream of text"""
        terminal_print(message, PrintType.LLM, end="", flush=True)
        if self.capture_active:
            self.capture += message

    def stream_chunk(self, thread_id: str, chunk: str) -> None:
        """
        Handle an incoming chunk of text from a streaming LLM response.
        
        Args:
            thread_id: The ID of the conversation thread this chunk belongs to.
            chunk: The piece of text from the AI's response.
        """
        terminal_print(chunk, PrintType.LLM, end="", flush=True)
        
    async def prompt_for_confirmation(self, prompt_text: str = "Apply these changes?", diff_lines: Optional[List[str]] = None, error_msg: str = None) -> Tuple[str, Optional[str]]:
        """
        Prompt the user for confirmation with options to apply, reject, request changes,
        edit the changes in a text editor, or accept all subsequent changes.
        
        Args:
            prompt_text: The text to display when prompting the user
            diff_lines: Optional list of diff lines (not used in CLI as diff is already displayed)
            error_msg: Optional error message to display if something has failed on a previous attempt
            
        Returns:
            Tuple of (response, message):
                - response: 'yes', 'no', 'request_change', 'edit', or 'accept_all'
                - message: User's feedback message when requesting changes,
                          or edited content when editing, None otherwise
        """
        if error_msg:
            self.print_text(f"Error: {error_msg}\nTry again or exit the code task by selecting 'no'")

        while True:
            response = input(f"\n{prompt_text} ✅ Yes [y] | ❌ No [n] | ✨ Accept All [a] | 🔄 Request Change [r] | ✏️  Edit [e]: ").lower().strip()
            if response in ('y', 'yes'):
                return 'yes', None
            elif response in ('n', 'no'):
                return 'no', None
            elif response in ('r', 'request', 'request_change'):
                self.print_text("Please enter your requested changes:", PrintType.INFO)
                message = input("> ")
                return 'request_change', message
            elif response in ('e', 'edit'):
                # This 'edit' response will lead to write_with_confirmation calling prompt_for_text_edit
                return 'edit', None
            elif response in ('a', 'accept_all'):
                return 'accept_all', None
            else:
                self.print_text("Please enter 'y', 'n', 'r', 'e', or 'a'", PrintType.ERROR)

    async def prompt_for_text_edit(self, content_to_edit: List[str], prompt_message: str = "Edit File Content") -> Optional[List[str]]:
        """
        Opens a text editor (curses-based for CLI) to allow the user to edit the provided content.

        Args:
            content_to_edit: A list of strings representing the lines of content to be edited.
            prompt_message: A message to display to the user before opening the editor.

        Returns:
            A list of strings representing the edited lines if the user saves changes,
            or None if the user cancels or an error occurs.
        """
        initial_text_str = "\n".join(content_to_edit)
        self.print_text(prompt_message, PrintType.INFO)

        if not is_curses_available():
            self.print_text("Curses editor is not available. Cannot edit.", PrintType.ERROR)
            return None

        self.print_text("Opening editor... (Alt+S to save, Alt+Q/ESC to cancel)", PrintType.INFO)
        
        success, edited_text_str = edit_text(initial_text_str)

        if success and edited_text_str is not None:
            return edited_text_str.splitlines()
        else:
            self.print_text("Edit cancelled or no changes made.", PrintType.INFO)
            return None

    async def prompt_steps(self, steps: Any) -> Any:
        """
        Prompt the user to confirm, edit, reprompt, or cancel the steps.
        Mirrors the behavior of the textual StepsScreen modal.
        Args:
            steps: The steps JSON object (dict)
        Returns:
            dict with keys: choice (accept/edit/reprompt/cancel), and steps or prompt as appropriate
        """
        explainer = (
            "These steps have been generated as a task list for your prompt.\n"
            "- Press continue to proceed with generating code for each step\n"
            "- Edit the steps and press 'Save Edits' to manually alter the steps. Ensure that you retain the current JSON format.\n"
            "- Use Re-Prompt to add additional prompt information and send it back to have new steps generated.\n"
            "- Press cancel to exit the current /code command.\n"
        )
        while True:
            self.print_text("\n===== Steps Review =====", PrintType.INFO)
            self.print_text(explainer, PrintType.INFO)
            try:
                steps_json_str = json.dumps(steps, indent=2)
            except Exception:
                steps_json_str = str(steps)
            self.print_text(steps_json_str, PrintType.LLM)
            self.print_text("\nWhat would you like to do?", PrintType.INFO)
            self.print_text("[c] Continue | [a] Accept All | [e] Edit | [r] Re-Prompt | [x] Cancel", PrintType.INFO)
            choice = input("Enter choice: ").strip().lower()
            if choice in ("c", "continue", "accept"):
                return {"choice": "accept", "steps": steps}
            elif choice in ("a", "accept_all"):
                return {"choice": "accept_all", "steps": steps}
            elif choice in ("e", "edit"):
                # Check if curses is available for a better editing experience
                if is_curses_available():
                    self.print_text("\nOpening curses editor. Alt+S to save, Alt+Q or ESC to cancel.", PrintType.INFO)
                    try:
                        success, edited_text = edit_text(steps_json_str)
                        if not success or edited_text is None:
                            self.print_text("Editing cancelled. Returning to menu.", PrintType.WARNING)
                            continue
                        
                        try:
                            edited_steps = json.loads(edited_text)
                            # Validate structure
                            if "steps" not in edited_steps:
                                raise ValueError("Failed to parse steps object: missing 'steps' key.")
                            if not isinstance(edited_steps["steps"], list):
                                raise ValueError("Steps must be a list of dictionaries.")
                            for step in edited_steps["steps"]:
                                if "operation_type" not in step:
                                    raise ValueError("Missing operation_type in a step.")
                                if "filename" not in step:
                                    raise ValueError("Missing filename in a step.")
                                if "target_location" not in step:
                                    raise ValueError("Missing target_location in a step.")
                                if "description" not in step:
                                    raise ValueError("Missing description in a step.")
                            return {"choice": "edit", "steps": edited_steps}
                        except Exception as e:
                            self.print_text(f"Invalid JSON or structure: {e}", PrintType.ERROR)
                            continue
                    except Exception as e:
                        self.print_text(f"Error using curses editor: {e}", PrintType.ERROR)
                        # Fall back to standard input method
                else:
                    # Curses not available, fall back to standard input method
                    pass
                
                # Standard input method (fallback)
                self.print_text("\nEnter the edited steps JSON below. Press Alt+S to submit, Alt+Q to cancel, or press Enter twice to finish:", PrintType.INFO)
                import termios
                import tty
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                edited_lines = []
                current_line = ""
                cancel_edit = False
                try:
                    tty.setraw(fd)
                    while True:
                        ch = sys.stdin.read(1)
                        if ch == '\x1b':  # ESC (potential Alt sequence)
                            # Try to read another char to see if it's Alt+S or Alt+Q
                            next_ch = sys.stdin.read(1)
                            if next_ch == 's' or next_ch == 'S':  # Alt+S
                                if current_line:
                                    edited_lines.append(current_line)
                                break
                            elif next_ch == 'q' or next_ch == 'Q':  # Alt+Q
                                cancel_edit = True
                                break
                            # If it was just ESC key, cancel
                            cancel_edit = True
                            break
                        elif ch == '\x11':  # Ctrl+Q
                            cancel_edit = True
                            break
                        elif ch in ('\r', '\n'):
                            # Enter key
                            if current_line == "":
                                # Detect double enter
                                if edited_lines and edited_lines[-1] == "":
                                    edited_lines.pop()
                                    break
                                edited_lines.append("")
                            else:
                                edited_lines.append(current_line)
                            current_line = ""
                        else:
                            current_line += ch
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                if cancel_edit:
                    self.print_text("Editing cancelled. Returning to menu.", PrintType.WARNING)
                    continue
                edited_text = "\n".join(edited_lines).strip()
                try:
                    edited_steps = json.loads(edited_text)
                    # Validate structure
                    if "steps" not in edited_steps:
                        raise ValueError("Failed to parse steps object: missing 'steps' key.")
                    if not isinstance(edited_steps["steps"], list):
                        raise ValueError("Steps must be a list of dictionaries.")
                    for step in edited_steps["steps"]:
                        if "operation_type" not in step:
                            raise ValueError("Missing operation_type in a step.")
                        if "filename" not in step:
                            raise ValueError("Missing filename in a step.")
                        if "target_location" not in step:
                            raise ValueError("Missing target_location in a step.")
                        if "description" not in step:
                            raise ValueError("Missing description in a step.")
                    return {"choice": "edit", "steps": edited_steps}
                except Exception as e:
                    self.print_text(f"Invalid JSON or structure: {e}", PrintType.ERROR)
                    continue
            elif choice in ("r", "reprompt"):
                self.print_text("\nEnter additional instructions for the prompt:", PrintType.INFO)
                user_text = input("> ").strip()
                if user_text:
                    return {"choice": "reprompt", "prompt": user_text}
                else:
                    self.print_text("No instructions entered. Returning to menu.", PrintType.WARNING)
                    continue
            elif choice in ("x", "cancel", "q", "quit"):
                return {"choice": "cancel"}
            else:
                self.print_text("Invalid choice. Please enter c, e, r, a, or x.", PrintType.ERROR)

    async def prompt_for_deletion(self, filepath: str) -> bool:
        """
        Prompt the user for confirmation before deleting a file.

        Args:
            filepath: The path to the file that will be deleted

        Returns:
            bool: True if the user confirms deletion, False otherwise
        """
        self.print_text(f"⚠️  DELETE operation requested for: {filepath}", PrintType.WARNING)

        while True:
            response = input(f"⚠️  Are you sure you want to delete '{filepath}'? [y/n]: ").strip().lower()
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no', ''):  # Default to no
                return False
            else:
                self.print_text("Please enter 'y' for yes or 'n' for no", PrintType.ERROR)

    async def signal_no_keys(self):
        setup_success = await run_first_time_setup(self.app)
        if not setup_success:
            self.print_text("Failed to set up required API keys. Exiting...", PrintType.ERROR)
            sys.exit(1)
        self.app.state.need_api_keys = not check_existing_keys(self.app)
        await self.app.initialize_services()
                
    async def signal_exit(self):
        """
        Signal to the CLI app that it should exit.
        For the CLI implementation, this directly exits the process.
        """
        # For CLI, we just exit the process directly
        sys.exit(0)

    def model_changed(self, model):
        pass

    def update_task_info(self, worker_id: str, update: dict = None) -> None:
        pass

    def chat_thread_update(self, thread_id):
        pass

    def code_context_update(self):
        pass

    def project_context_changed(self, is_enabled: bool) -> None:
        pass

    def providers_updated(self) -> None:
        pass

    def model_list_updated(self) -> None:
        pass