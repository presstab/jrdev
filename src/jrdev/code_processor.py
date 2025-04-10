import json
import os
from typing import Any, Dict, List, Set

from jrdev.llm_requests import stream_request
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.file_utils import requested_files, get_file_contents, cutoff_string
from jrdev.file_operations.process_ops import apply_file_changes
from jrdev.ui.ui import PrintType, print_steps
from jrdev.message_builder import MessageBuilder


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

    async def process(self, user_task: str) -> None:
        """
        The main orchestration method.
        This method performs:
          1. Sending the initial request (the user’s task with any context)
          2. Interpreting the LLM response to see if file changes are requested
          3. Requesting file content if needed, parsing returned steps, and executing each step
          4. Validating the changed files at the end
        """
        try:
            initial_response = await self.send_initial_request(user_task)
            await self.process_code_response(initial_response, user_task)
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
        builder.start_user_section(f"The user is seeking guidance for this task to complete: {user_task}")
        builder.load_user_prompt("analyze_task_return_getfiles")
        builder.add_project_files()
        builder.finalize_user_section()
        messages = builder.build()

        model_name = self.profile_manager.get_model("advanced_reasoning")
        self.app.ui.print_text(f"\n{model_name} is processing the request... (advanced_reasoning profile)", PrintType.PROCESSING)
        response_text = await stream_request(self.app, model_name, messages, task_id=self.worker_id)
        self.app.ui.print_text("", PrintType.INFO)
        return response_text

    async def process_code_response(self, response_text: str, user_task: str) -> None:
        """
        Process the LLM’s initial response. If the response includes file requests,
        this triggers the file request workflow.
        """
        files_to_send = requested_files(response_text)
        if not files_to_send:
            raise Exception("Get files failed")
        if files_to_send:
            # Send requested files and request STEPS to be created
            self.app.logger.info(f"File request detected: {files_to_send}")
            file_response = await self.send_file_request(files_to_send, user_task, response_text)
            steps = await self.parse_steps(file_response, files_to_send)
            if "steps" not in steps or not steps["steps"]:
                raise Exception("No valid steps found in response.")
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
                new_changes = await self.complete_step(step, files_to_send)
                if new_changes:
                    completed_steps.append(i)
                    changed_files.update(new_changes)
                else:
                    failed_steps.append((i, step))

            # Second pass for any steps that did not succeed on the first try.
            for idx, step in failed_steps:
                self.app.ui.print_text(f"Retrying step {idx + 1}", PrintType.PROCESSING)
                print_steps(self.app, steps, completed_steps, current_step=idx)
                new_changes = await self.complete_step(step, files_to_send)
                if new_changes:
                    completed_steps.append(idx)
                    changed_files.update(new_changes)

            print_steps(self.app, steps, completed_steps)
            if changed_files:
                await self.validate_changed_files(changed_files)
            else:
                self.app.logger.info("No files were changed during processing.")
        else:
            self.app.logger.info("No file changes were requested by the LLM response.")

    async def complete_step(self, step: Dict, files_to_send: List[str], retry_message: str = None) -> List[str]:
        """
        Process an individual step:
          - Obtain the current file content.
          - Request a code change from the LLM.
          - Attempt to apply the change.
          - If the change isn’t accepted, optionally retry.
        Returns a list of files changed or an empty list if the step failed.
        """
        file_content = get_file_contents(files_to_send)
        code_response = await self.request_code(step, file_content, retry_message)
        try:
            result = await self.check_and_apply_code_changes(code_response)
            if result.get("success"):
                return result.get("files_changed", [])
            if "change_requested" in result:
                # Use change-request feedback to retry the step.
                retry_message = result["change_requested"]
                self.app.ui.print_text("Retrying step with additional feedback...", PrintType.WARNING)
                return await self.complete_step(step, files_to_send, retry_message)
            raise Exception("Failed to apply code changes in step.")
        except Exception as e:
            self.app.ui.print_text(f"Step failed: {str(e)}", PrintType.ERROR)
            return []

    async def request_code(self, change_instruction: Dict, file_content: str, additional_prompt: str = None) -> str:
        """
        Construct and send a code change request.
        Uses an operation-specific prompt (loaded from a markdown file) and a template prompt.
        """
        op_type = change_instruction.get("operation_type")
        operation_prompt = PromptManager.load(f"operations/{op_type.lower()}")
        dev_msg_template = PromptManager.load("implement_step")
        if dev_msg_template:
            dev_msg = dev_msg_template.replace("{operation_prompt}", operation_prompt)
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
        response = await stream_request(self.app, model, messages, task_id=self.worker_id, print_stream=True, json_output=True)
        return response

    async def check_and_apply_code_changes(self, response_text: str) -> Dict:
        """
        Extract and parse the JSON snippet for code changes from the LLM response,
        then apply the file changes.
        """
        try:
            json_block = cutoff_string(response_text, "```json", "```")
            changes = json.loads(json_block)
        except Exception as e:
            raise Exception(f"Parsing failed in code changes: {str(e)}\n Blob:{json_block}\n")
        if "changes" in changes:
            return await apply_file_changes(self.app, changes)
        return {"success": False}

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
        response = await stream_request(self.app, model, messages, task_id=self.worker_id)
        self.app.ui.print_text("", PrintType.INFO)
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
        validation_response = await stream_request(
            self.app, model, messages, task_id=self.worker_id, print_stream=False
        )
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
