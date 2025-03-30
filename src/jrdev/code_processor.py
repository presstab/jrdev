import os
from typing import Any, Dict, List, Set

from jrdev.llm_requests import stream_request
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.file_utils import requested_files, get_file_contents, cutoff_string, manual_json_parse
from jrdev.file_operations.process_ops import apply_file_changes
from jrdev.ui.ui import terminal_print, PrintType, print_steps


class CodeProcessor:
    def __init__(self, terminal: Any):
        """
        Initialize the CodeProcessor with the terminal instance.
        The terminal object should provide access to logging, message history,
        project_files, context, model information, and message-history management.
        """
        self.terminal = terminal

    async def process(self, user_task: str) -> None:
        """
        The main orchestration method.
        This method performs:
          1. Sending the initial request (the user’s task with any context)
          2. Interpreting the LLM response to see if file changes are requested
          3. Requesting file content if needed, parsing returned steps, and executing each step
          4. Validating the changed files at the end
        """
        # Save current message history in case we need to revert later.
        current_history = self.terminal.message_history()
        try:
            initial_response = await self.send_initial_request(user_task)
            await self.process_code_response(initial_response, user_task)
        except Exception as e:
            self.terminal.logger.error(f"Error in CodeProcessor: {str(e)}")
            terminal_print(f"Error processing code: {str(e)}", PrintType.ERROR)
        finally:
            # Restore the original message history.
            self.terminal.set_message_history(current_history)

    async def send_initial_request(self, user_task: str) -> str:
        """
        Build the initial message using the user task and any project context,
        then send it to the LLM.
        """
        # Start with a base user message.
        user_message = "Here is the task to complete: " + user_task

        # Append any project context available in terminal.project_files.
        for key, filename in self.terminal.project_files.items():
            if os.path.exists(filename):
                try:
                    with open(filename, "r") as f:
                        content = f.read()
                    user_message += f"\n\n{key.upper()}:\n{content}"
                except Exception as e:
                    warning_msg = f"Could not read {filename}: {str(e)}"
                    self.terminal.logger.warning(warning_msg)
                    terminal_print(f"Warning: {warning_msg}", PrintType.WARNING)

        # Append additional context from terminal.context if available.
        if self.terminal.context:
            context_section = "\n\nUSER CONTEXT:\n"
            for i, ctx in enumerate(self.terminal.context):
                context_section += f"\n--- Context File {i + 1}: {ctx['name']} ---\n{ctx['content']}\n"
            user_message += context_section

        # Load a system prompt (e.g. "analyze_task_return_getfiles") to guide the LLM.
        dev_prompt_modifier = PromptManager.load("analyze_task_return_getfiles")
        messages = []
        if dev_prompt_modifier:
            messages.append({"role": "system", "content": dev_prompt_modifier})
        messages.append({"role": "user", "content": user_message})

        model_name = self.terminal.model
        terminal_print(f"\n{model_name} is processing the request...", PrintType.PROCESSING)
        response_text = await stream_request(self.terminal, model_name, messages)
        terminal_print("", PrintType.INFO)
        return response_text

    async def process_code_response(self, response_text: str, user_task: str) -> None:
        """
        Process the LLM’s initial response. If the response includes file requests,
        this triggers the file request workflow.
        """
        files_to_send = requested_files(response_text)
        if files_to_send:
            self.terminal.logger.info(f"File request detected: {files_to_send}")
            file_response = await self.send_file_request(files_to_send, user_task, response_text)
            steps = await self.parse_steps(file_response, files_to_send)
            if "steps" not in steps or not steps["steps"]:
                raise Exception("No valid steps found in response.")
            print_steps(self.terminal, steps)

            # Process each step (first pass)
            completed_steps = []
            changed_files: Set[str] = set()
            failed_steps = []
            for i, step in enumerate(steps["steps"]):
                print_steps(self.terminal, steps, completed_steps, current_step=i)
                terminal_print(
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
                terminal_print(f"Retrying step {idx + 1}", PrintType.PROCESSING)
                print_steps(self.terminal, steps, completed_steps, current_step=idx)
                new_changes = await self.complete_step(step, files_to_send)
                if new_changes:
                    completed_steps.append(idx)
                    changed_files.update(new_changes)

            print_steps(self.terminal, steps, completed_steps)
            if changed_files:
                await self.validate_changed_files(changed_files)
            else:
                self.terminal.logger.info("No files were changed during processing.")
        else:
            self.terminal.logger.info("No file changes were requested by the LLM response.")

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
            result = self.check_and_apply_code_changes(code_response)
            if result.get("success"):
                return result.get("files_changed", [])
            if "change_requested" in result:
                # Use change-request feedback to retry the step.
                retry_message = result["change_requested"]
                terminal_print("Retrying step with additional feedback...", PrintType.WARNING)
                return await self.complete_step(step, files_to_send, retry_message)
            raise Exception("Failed to apply code changes in step.")
        except Exception as e:
            terminal_print(f"Step failed: {str(e)}", PrintType.ERROR)
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
            self.terminal.logger.error(error_msg)
            raise KeyError(error_msg)

        prompt = (
            f"You have been tasked with using the {op_type} operation to {description}. This should be "
            f"applied to the supplied file {filename} and you will need to locate the proper location in "
            f"the code to apply this change. The target location is {location}. "
            "Operations should only be applied to this location, or else the task will fail."
        )
        if additional_prompt:
            prompt = f"{prompt} {additional_prompt}"

        messages = []
        messages.append({"role": "system", "content": dev_msg})
        messages.append({"role": "user", "content": file_content})
        messages.append({"role": "user", "content": prompt})
        self.terminal.logger.info(f"Sending code request to {self.terminal.model}")
        terminal_print(f"\nSending code request to {self.terminal.model}...", PrintType.PROCESSING)
        response = await stream_request(self.terminal, self.terminal.model, messages)
        terminal_print("", PrintType.INFO)
        self.terminal.add_message_history(response, is_assistant=True)
        return response

    def check_and_apply_code_changes(self, response_text: str) -> Dict:
        """
        Extract and parse the JSON snippet for code changes from the LLM response,
        then apply the file changes.
        """
        try:
            json_block = cutoff_string(response_text, "```json", "```")
            changes = manual_json_parse(json_block)
        except Exception as e:
            raise Exception(f"Parsing failed in code changes: {str(e)}")
        if "changes" in changes:
            return apply_file_changes(changes)
        return {"success": False}

    async def send_file_request(self, files_to_send: List[str], user_task: str, initial_response: str) -> str:
        """
        When the initial request detects file changes,
        send the content of those files along with the task details back to the LLM.
        """
        files_content = get_file_contents(files_to_send)
        dev_msg = PromptManager.load("create_steps")
        messages = []
        messages.append({"role": "system", "content": dev_msg})
        messages.append({"role": "user", "content": f"Task To Accomplish: {user_task}"})
        messages.append({"role": "assistant", "content": initial_response})
        messages.append({"role": "user", "content": files_content})
        self.terminal.logger.info(f"Sending file contents to {self.terminal.model}")
        terminal_print(f"\nSending requested files to {self.terminal.model}...", PrintType.PROCESSING)
        response = await stream_request(self.terminal, self.terminal.model, messages)
        terminal_print("", PrintType.INFO)
        return response

    async def parse_steps(self, steps_text: str, filelist: List[str]) -> Dict:
        """
        Extract and parse the JSON steps from the LLM response.
        Also, verify that every file referenced in steps exists in the provided filelist.
        """
        json_content = cutoff_string(steps_text, "```json", "```")
        steps_json = manual_json_parse(json_content)

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
            self.terminal.logger.warning(f"Files not found: {missing_files}")
            steps_json["missing_files"] = missing_files
        return steps_json

    async def validate_changed_files(self, changed_files: Set[str]) -> None:
        """
        Validate that the files changed by the LLM are not malformed.
        Sends the modified file contents to the LLM using a validation prompt.
        """
        self.terminal.logger.info("Validating changed files")
        terminal_print("\nValidating changed files...", PrintType.PROCESSING)
        files_content = get_file_contents(list(changed_files))
        validation_prompt = PromptManager.load("validator")
        messages = [
            {"role": "system", "content": validation_prompt},
            {"role": "user", "content": f"Please validate these files:\n{files_content}"}
        ]
        original_model = self.terminal.model
        # Temporarily switch to a model used for validation.
        self.terminal.model = "qwen-2.5-coder-32b"
        validation_response = await stream_request(
            self.terminal, self.terminal.model, messages, print_stream=False
        )
        self.terminal.logger.info(f"Validation response: {validation_response}")
        if validation_response.strip().startswith("VALID"):
            terminal_print("✓ Files validated successfully", PrintType.SUCCESS)
        elif "INVALID" in validation_response:
            reason = (
                validation_response.split("INVALID:")[1].strip() if ":" in validation_response
                else "Unspecified error"
            )
            terminal_print(f"⚠ Files may be malformed: {reason}", PrintType.ERROR)
        else:
            terminal_print("⚠ Could not determine file validation status", PrintType.WARNING)
        self.terminal.model = original_model
