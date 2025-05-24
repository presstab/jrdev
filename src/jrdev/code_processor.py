from asyncio import CancelledError
import json
import os
from typing import Any, Dict, List, Set
from difflib import unified_diff

from jrdev.llm_requests import generate_llm_response
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.file_utils import requested_files, get_file_contents, cutoff_string
from jrdev.file_operations.process_ops import apply_file_changes, CodeTaskCancelled
from jrdev.ui.ui import PrintType, print_steps
from jrdev.message_builder import MessageBuilder

class Reprompt(Exception):
    """
    Exception to signal that the user has sent a new prompt
    """
    pass

class CodeProcessor:
    def __init__(self, app: Any, worker_id=None):
        """
        Initialize the CodeProcessor with the application instance.
        The app object should provide access to logging, message history,
        project_files, context, model information, and message-history management.
        """
        self.app = app
        self.profile_manager = app.profile_manager()
        self.worker_id = worker_id
        self.sub_task_count = 0
        self._accept_all_active = False  # Track if 'Accept All' is active for this instance
        self.files_validated = False
        self.files_original: Dict[str, str] = {} # Stores original file content: {filepath: content}

        # get custom user set code context, which should be cleared from app state after fetching
        self.user_context = app.get_code_context()
        app.clear_code_context()

    async def process(self, user_task: str) -> None:
        """
        The main orchestration method.
        This method performs:
          1. Sending the initial request (the user’s task with any context)
          2. Interpreting the LLM response to see if file changes are requested
          3. Requesting file content if needed, parsing returned steps, and executing each step
          4. Validating the changed files at the end (only at the top level)
        """
        try:
            initial_response = await self.send_initial_request(user_task)
            await self.process_code_response(initial_response, user_task)
        except CodeTaskCancelled:
            raise
        except Reprompt as additional_prompt:
            await self.process(f"{user_task} {additional_prompt}")
        except CancelledError:
            # worker.cancel() should kill everything
            raise
        except Exception as e:
            self.app.logger.error(f"Error in CodeProcessor: {str(e)}")
            self.app.ui.print_text(f"Error processing code: {str(e)}", PrintType.ERROR)

    async def send_initial_request(self, user_task: str) -> str:
        """
        Build the initial message using the user task and any project context,
        then send it to the LLM.
        """
        # Use MessageBuilder for consistent message construction
        builder = MessageBuilder(self.app)
        for file in self.user_context:
            builder.add_file(file)
        builder.start_user_section(f"The user is seeking guidance for this task to complete: {user_task}")
        builder.load_user_prompt("analyze_task_return_getfiles")
        builder.add_project_files()
        builder.finalize_user_section()
        messages = builder.build()

        model_name = self.profile_manager.get_model("advanced_reasoning")
        self.app.ui.print_text(f"\n{model_name} is processing the request... (advanced_reasoning profile)", PrintType.PROCESSING)
        sub_task_str = None
        if self.worker_id:
            # create a sub task id
            self.sub_task_count += 1
            sub_task_str = f"{self.worker_id}:{self.sub_task_count}"
            self.app.ui.update_task_info(self.worker_id, update={"new_sub_task": sub_task_str, "description": "analyze request"})

        # send request
        response_text = await generate_llm_response(self.app, model_name, messages, task_id=sub_task_str)

        # mark sub_task complete
        if self.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        return response_text

    async def process_code_response(self, response_text: str, user_task: str) -> None:
        """
        Process the LLM’s initial response. If the response includes file requests,
        this triggers the file request workflow.
        """
        files_to_send = requested_files(response_text)
        if not files_to_send:
            # use a fast model to parse response and see if it is salvageable
            salvaged_response = await self.salvage_get_files(response_text)
            files_to_send = requested_files(salvaged_response)
            if not files_to_send and not self.user_context:
                raise Exception("Get files failed")
        if self.user_context:
            self.app.logger.info(f"User context added: {self.user_context}")
        for file in self.user_context:
            if file not in files_to_send:
                files_to_send.append(file)

        # Check that included files are sufficient
        files_to_send = await self.ask_files_sufficient(files_to_send, user_task)

        self.app.logger.info(f"File request detected: {files_to_send}")

        # Store original content of files before any changes
        for filepath_to_store in files_to_send:
            if os.path.exists(filepath_to_store):
                try:
                    with open(filepath_to_store, 'r', encoding='utf-8') as f_original:
                        original_content = f_original.read()
                    self.files_original[filepath_to_store] = original_content
                except Exception as e:
                    self.app.logger.warning(f"CodeProcessor: Could not read original content for {filepath_to_store}: {e}")
                    self.files_original[filepath_to_store] = "" # Store empty string if reading fails
            else:
                # File might be created by a 'NEW' operation, so its original content is empty
                self.files_original[filepath_to_store] = ""

        # Send requested files and request STEPS to be created
        file_response = await self.send_file_request(files_to_send, user_task, response_text)
        steps = None
        try:
            steps = await self.parse_steps(file_response, files_to_send)
            if "steps" not in steps or not steps["steps"]:
                raise Exception("No valid steps found in response.")
        except Exception as e:
            self.app.logger.error(f"Failed to parse steps\nerr: {e}\nsteps:\n{file_response}")
            raise

        # Prompt user to accept or edit steps, unless accept_all is active
        if self._accept_all_active:
            self.app.ui.print_text("Accept All is active, skipping steps confirmation.", PrintType.INFO)
            # Keep existing steps, proceed as if accepted
        else:
            user_result = await self.app.ui.prompt_steps(steps)
            user_choice = user_result.get("choice")

            if user_choice == "edit":
                steps = user_result.get("steps")
            elif user_choice == "accept":
                steps = user_result.get("steps")
            elif user_choice == "accept_all":
                steps = user_result.get("steps")
                # Set the flag for future operations
                self._accept_all_active = True
                # Proceed as if accepted
            elif user_choice == "cancel":
                raise CodeTaskCancelled()
            elif user_choice == "reprompt":
                additional_prompt = user_result.get("prompt")
                raise Reprompt(additional_prompt)
            else: # Handle unexpected choice
                 raise Exception(f"Unexpected choice from prompt_steps: {user_choice}")

        # If we reach here, it means the choice was accept, edit, or accept_all (or skipped due to flag)
        print_steps(self.app, steps)

        # Process each step (first pass)
        completed_steps = []
        changed_files: Set[str] = set()
        failed_steps = []
        for i, step in enumerate(steps["steps"]):
            print_steps(self.app, steps, completed_steps, current_step=i)
            self.app.ui.print_text(
                f"Working on step {i + 1}: {step.get('operation_type')} for {step.get('filename')}",
                PrintType.PROCESSING
            )

            coding_files = list(files_to_send) # Start with the initial context files
            for file in changed_files: # Add any files already modified in this run
                if file not in coding_files:
                    coding_files.append(file)

            # send coding task to LLM
            new_changes = await self.complete_step(step, user_task, coding_files)
            if new_changes:
                completed_steps.append(i)
                changed_files.update(new_changes)
            else:
                failed_steps.append((i, step))

        # Second pass for any steps that did not succeed on the first try.
        for idx, step in failed_steps:
            self.app.ui.print_text(f"Retrying step {idx + 1}", PrintType.PROCESSING)
            print_steps(self.app, steps, completed_steps, current_step=idx)
            new_changes = await self.complete_step(step, user_task, files_to_send)
            if new_changes:
                completed_steps.append(idx)
                changed_files.update(new_changes)

        print_steps(self.app, steps, completed_steps)
        if changed_files:
            review_response = await self.review_changes(user_task, files_to_send, changed_files)
            try:
                json_content = cutoff_string(review_response, "```json", "```")
                review = json.loads(json_content)
                review_passed = review.get("success", False)
                if not review_passed:
                    # send review comments back to the analysis
                    reason = review.get("reason", None)
                    action = review.get("action", None)
                    if reason and action:
                        change_request = (f"The user requested changes and an attempt was made to fulfill the change request. The reviewer determined that the changes "
                                          f"failed because {reason}. The reviewer requests that this action be taken to complete the task: {action}. This is the user task: {user_task}")
                        try:
                            await self.process(change_request)
                        except CodeTaskCancelled:
                            raise
                    else:
                        self.app.logger.info(f"Malformed change request from reviewer:\n{review}")

            except Exception as e:
                # todo try again?
                self.app.logger.error(f"failed to parse review: {review_response}")

            # only perform validation once
            if not self.files_validated:
                await self.validate_changed_files(changed_files)
                self.files_validated = True
        else:
            self.app.logger.info("No files were changed during processing.")

    async def complete_step(self, step: Dict, user_task: str, files_to_send: List[str], retry_message: str = None) -> List[str]:
        """
        Process an individual step:
          - Obtain the current file content.
          - Request a code change from the LLM.
          - Attempt to apply the change.
          - If the change isn’t accepted, optionally retry.
        Returns a list of files changed or an empty list if the step failed.
        """
        file_content = get_file_contents(files_to_send)
        code_response = await self.request_code(change_instruction=step, user_task=user_task, file_content=file_content, additional_prompt=retry_message)
        try:
            result = await self.check_and_apply_code_changes(code_response)
            if result.get("success"):
                return result.get("files_changed", [])
            if "change_requested" in result:
                # Use change-request feedback to retry the step.
                retry_message = result["change_requested"]
                self.app.ui.print_text("Retrying step with additional feedback...", PrintType.WARNING)
                return await self.complete_step(step, user_task, files_to_send, retry_message)
            raise Exception("Failed to apply code changes in step.")
        except CodeTaskCancelled as e:
            self.app.ui.print_text(f"Code task cancelled by user: {str(e)}", PrintType.WARNING)
            raise
        except CancelledError:
            # worker.cancel() should kill everything
            raise
        except Exception as e:
            self.app.ui.print_text(f"Step failed: {str(e)}", PrintType.ERROR)
            return []

    async def request_code(self, change_instruction: Dict, user_task: str, file_content: str, additional_prompt: str = None) -> str:
        """
        Construct and send a code change request.
        Uses an operation-specific prompt (loaded from a markdown file) and a template prompt.
        """
        op_type = change_instruction.get("operation_type")
        operation_prompt = PromptManager.load(f"operations/{op_type.lower()}")
        dev_msg_template = PromptManager.load("implement_step")
        if dev_msg_template:
            dev_msg = dev_msg_template.replace("{operation_prompt}", operation_prompt)
            dev_msg = dev_msg.replace("{user_task}", user_task)
        else:
            dev_msg = operation_prompt

        description = change_instruction.get("description")
        filename = change_instruction.get("filename")
        location = change_instruction.get("target_location")
        if not all([description, filename, location]):
            error_msg = "Missing required fields in change instruction."
            self.app.logger.error(error_msg)
            raise KeyError(error_msg)

        prompt = (
            f"You have been tasked with using the {op_type} operation to {description}. This should be "
            f"applied to the supplied file {filename} and you will need to locate the proper location in "
            f"the code to apply this change. The target location is {location}. "
            "Operations should only be applied to this location, or else the task will fail."
        )
        if additional_prompt:
            prompt = f"{prompt} {additional_prompt}"

        # Use MessageBuilder to construct messages
        builder = MessageBuilder(self.app)
        builder.start_user_section()
        builder.add_system_message(dev_msg)
        builder.append_to_user_section(file_content)
        builder.append_to_user_section(prompt)
        messages = builder.build()

        # Send request
        model = self.profile_manager.get_model("advanced_coding")
        self.app.logger.info(f"Sending code request to {model}")
        self.app.ui.print_text(f"\nSending code request to {model} (advanced_coding profile)...\n", PrintType.PROCESSING)

        sub_task_str = None
        if self.worker_id:
            # create a sub task id
            self.sub_task_count += 1
            sub_task_str = f"{self.worker_id}:{self.sub_task_count }"
            self.app.ui.update_task_info(self.worker_id, update={"new_sub_task": sub_task_str, "description": op_type})

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str, print_stream=True, json_output=True)

        # mark sub_task complete
        if self.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        return response

    async def check_and_apply_code_changes(self, response_text: str) -> Dict:
        """
        Extract and parse the JSON snippet for code changes from the LLM response,
        then apply the file changes.
        If the user cancels the code task (selects 'no'), the code task is ended immediately.
        """
        try:
            json_block = cutoff_string(response_text, "```json", "```")
            changes = json.loads(json_block)
        except CancelledError:
            # worker.cancel() should kill everything
            raise
        except Exception as e:
            raise Exception(f"Parsing failed in code changes: {str(e)}\n Blob:{json_block}\n")

        if "cancel_step" in changes:
            # AI model has determined this step is already completed
            reason = changes["cancel_step"]
            self.app.logger.warning(f"Model determined step was already complete. Reason:{reason}")
            return {"success": True, "cancel_step": True, "files_changed": []}
        if "changes" in changes:
            try:
                # Pass self (CodeProcessor instance) to manage accept_all state
                return await apply_file_changes(self.app, changes, self)
            except CodeTaskCancelled as e:
                # User selected 'no' during confirmation, end code task immediately
                self.app.logger.warning(f"Code task cancelled by user: {str(e)}")
                raise
        return {"success": False}

    async def salvage_get_files(self, bad_message: str):
        """
        Occasionally, getfiles will fail because of bad formatting. Attempt to salvage the message.
        """
        builder = MessageBuilder(self.app)
        builder.load_system_prompt("get_files_format")
        builder.start_user_section()
        builder.append_to_user_section(f"Parse the included message to see what files are being requested. You must only respond with the correct format of getfiles. Extract files from this message {bad_message}")
        builder.add_tree()
        messages = builder.build()

        model = self.profile_manager.get_model("quick_reasoning")
        self.app.logger.info(f"Attempting to reformat file request with {model}")
        self.app.ui.print_text(f"\nAttempting to reformat file request with {model} (quick_reasoning profile)...", PrintType.PROCESSING)

        sub_task_str = None
        if self.worker_id:
            # create a sub task id
            self.sub_task_count += 1
            sub_task_str = f"{self.worker_id}:{self.sub_task_count}"
            self.app.ui.update_task_info(self.worker_id, update={"new_sub_task": sub_task_str, "description": "format file request"})

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str)

        # mark sub_task complete
        if self.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        return response

    async def ask_files_sufficient(self, files: List[str], user_task: str):
        """
        Is the current list of files sufficient to complete the task?
        """
        builder = MessageBuilder(self.app)
        builder.load_system_prompt("get_files_check")
        builder.start_user_section()
        builder.append_to_user_section(f"***User Task***: {user_task}")
        builder.add_tree()
        for file in files:
            builder.add_file(file)
        messages = builder.build()

        model = self.profile_manager.get_model("advanced_reasoning")
        self.app.logger.info(f"Analyzing if more files are needed, using {model}")
        self.app.ui.print_text(f"\nAnalyzing if more files are needed, using {model} (advanced_reasoning profile)...", PrintType.PROCESSING)

        sub_task_str = None
        if self.worker_id:
            # create a sub task id
            self.sub_task_count += 1
            sub_task_str = f"{self.worker_id}:{self.sub_task_count}"
            self.app.ui.update_task_info(self.worker_id, update={"new_sub_task": sub_task_str, "description": "files check"})

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str)
        self.app.logger.info(f"additional files response:\n {response}")

        # mark sub_task complete
        if self.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        json_content = cutoff_string(response, "```json", "```")
        tool_calls = json.loads(json_content)
        if tool_calls:
            tool = tool_calls.get("tool")
            if tool and tool == "read":
                file_list = tool_calls.get("file_list", [])
                if file_list:
                    add_files = requested_files(f"get_files {str(file_list)}")
                    for file in add_files:
                        if file not in files:
                            files.append(file)
                            self.app.logger.info(f"Adding file {file}")
        return files

    async def send_file_request(self, files_to_send: List[str], user_task: str, initial_response: str) -> str:
        """
        When the initial request detects file changes,
        send the content of those files along with the task details back to the LLM.
        """
        builder = MessageBuilder(self.app)
        builder.start_user_section()
        builder.append_to_user_section(f"Initial Plan: {initial_response}")

        # Add file contents
        for file in files_to_send:
            builder.add_file(file)

        builder.load_user_prompt("create_steps")
        builder.append_to_user_section(f"**Task**: {user_task}")
        messages = builder.build()

        model = self.profile_manager.get_model("advanced_reasoning")
        self.app.logger.info(f"Sending file contents to {model}")
        self.app.ui.print_text(f"\nSending requested files to {model} (advanced_reasoning profile)...", PrintType.PROCESSING)

        sub_task_str = None
        if self.worker_id:
            # create a sub task id
            self.sub_task_count += 1
            sub_task_str = f"{self.worker_id}:{self.sub_task_count}"
            self.app.ui.update_task_info(self.worker_id, update={"new_sub_task": sub_task_str, "description": "create plan"})

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str)

        # mark sub_task complete
        if self.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        return response

    async def parse_steps(self, steps_text: str, filelist: List[str]) -> Dict:
        """
        Extract and parse the JSON steps from the LLM response.
        Also, verify that every file referenced in steps exists in the provided filelist.
        """
        json_content = cutoff_string(steps_text, "```json", "```")
        steps_json = json.loads(json_content)

        # Check for missing files in the step instructions.
        missing_files = []
        if "steps" in steps_json:
            for step in steps_json["steps"]:
                filename = step.get("filename")
                if filename:
                    basename = os.path.basename(filename)
                    if not any((os.path.basename(f) == basename or f == filename) for f in filelist):
                        missing_files.append(filename)
        if missing_files:
            self.app.logger.warning(f"Files not found: {missing_files}")
            steps_json["missing_files"] = missing_files
        return steps_json

    async def review_changes(self, initial_prompt: str, context_files: List[str], changed_files: Set[str]) -> str:
        """
        Review all changes and analyze whether the task has adequately been completed
        Args:
            initial_prompt: The user's original task prompt.
            context_files: List of files initially provided as context for the task.
            changed_files: Set of file paths that were actually modified or created.

        Returns:
            str: The LLM's review response.
        """
        full_file_list_for_context = list(context_files)
        for filepath_changed in changed_files:
            if filepath_changed not in full_file_list_for_context:
                full_file_list_for_context.append(filepath_changed)

        builder = MessageBuilder(self.app)
        builder.load_system_prompt("review_changes")

        all_diff_texts = []
        for filepath in changed_files:
            original_content_str = self.files_original.get(filepath, "")

            current_content_str = ""
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f_current:
                        current_content_str = f_current.read()
                except Exception as e:
                    self.app.logger.warning(f"CodeProcessor: Could not read current content for {filepath} during review: {e}")

            original_lines = original_content_str.splitlines(True)
            current_lines = current_content_str.splitlines(True)

            # Generate diff if there are any changes or if it's a new file
            if original_lines != current_lines:
                diff_output = list(unified_diff(
                    original_lines,
                    current_lines,
                    fromfile=f"a/{filepath}",
                    tofile=f"b/{filepath}",
                    n=3
                ))

                if diff_output: # Ensure diff is not empty
                    diff_text_for_file = "".join(diff_output)
                    all_diff_texts.append(f"--- Diff for {filepath} ---\n{diff_text_for_file}\n")

        if all_diff_texts:
            full_diffs_report = "\n".join(all_diff_texts)
            builder.append_to_user_section(f"\n\n**Summary of Changes Made (Diffs):**\n{full_diffs_report}")
            self.app.logger.info(f"{full_diffs_report}")

        builder.append_to_user_section(f"***User Request***: {initial_prompt}")
        for file_for_context in full_file_list_for_context:
            builder.add_file(file_for_context) # This adds current content of files for LLM context

        messages = builder.build()

        # Validation Model
        model = self.profile_manager.get_model("advanced_reasoning")
        self.app.logger.info(f"Checking work: {model}")
        self.app.ui.print_text(f"\nChecking code changes to ensure completion with {model} (advanced_reasoning profile)", PrintType.PROCESSING)

        sub_task_str = None
        if self.worker_id:
            # create a sub task id
            self.sub_task_count += 1
            sub_task_str = f"{self.worker_id}:{self.sub_task_count}"
            self.app.ui.update_task_info(self.worker_id, update={"new_sub_task": sub_task_str, "description": "check work"})

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str, print_stream=False)

        # mark sub_task complete
        if self.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})
        self.app.ui.print_text(f"Check Work:\n {response}")

        return response

    async def validate_changed_files(self, changed_files: Set[str]) -> None:
        """
        Validate that the files changed by the LLM are not malformed.
        Sends the modified file contents to the LLM using a validation prompt.
        """
        files_content = get_file_contents(list(changed_files))
        builder = MessageBuilder(self.app)
        builder.load_system_prompt("validator")
        builder.add_user_message(f"Please validate these files:\n{files_content}")
        messages = builder.build()

        # Validation Model
        model = self.profile_manager.get_model("intermediate_reasoning")
        self.app.logger.info(f"Validating changed files with {model}")
        self.app.ui.print_text(f"\nValidating changed files with {model} (intermediate_reasoning profile)", PrintType.PROCESSING)

        sub_task_str = None
        if self.worker_id:
            # create a sub task id
            self.sub_task_count += 1
            sub_task_str = f"{self.worker_id}:{self.sub_task_count}"
            self.app.ui.update_task_info(self.worker_id, update={"new_sub_task": sub_task_str, "description": "validate"})

        validation_response = await generate_llm_response(
            self.app, model, messages, task_id=sub_task_str, print_stream=False
        )

        # mark sub_task complete
        if self.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        self.app.logger.info(f"Validation response: {validation_response}")
        if validation_response.strip().startswith("VALID"):
            self.app.ui.print_text("✓ Files validated successfully", PrintType.SUCCESS)
        elif "INVALID" in validation_response:
            reason = (
                validation_response.split("INVALID:")[1].strip() if ":" in validation_response
                else "Unspecified error"
            )
            self.app.ui.print_text(f"⚠ Files may be malformed: {reason}", PrintType.ERROR)
        else:
            self.app.ui.print_text("⚠ Could not determine file validation status", PrintType.WARNING)