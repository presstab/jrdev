import json
from asyncio import CancelledError
from typing import Any, Dict, List, Set, Tuple

from jrdev.agents.pipeline.stage import Stage
from jrdev.core.exceptions import CodeTaskCancelled
from jrdev.file_operations.apply_changes import apply_file_changes
from jrdev.file_operations.delete import delete_with_confirmation
from jrdev.file_operations.file_utils import cutoff_string, get_file_contents
from jrdev.messages.message_builder import MessageBuilder
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType, print_steps


class ExecutePhase(Stage):
    """
    Carry out the “plan” by requesting code changes from the LLM and applying them to disk.

    Responsibilities:
      - Walk through each step in the plan JSON.
      - For DELETE steps:
          • Prompt the user to confirm or cancel removal.
          • Delete the file if approved, or record a user‐cancelled marker.
      - For ADD/MODIFY/etc. steps:
          • Collect the latest contents of all relevant files (initial + any that have already changed).
          • Send a coding prompt to the LLM (with retry logic on failure).
          • Parse the returned JSON diff and apply it via the filesystem.
      - Keep track of which files were created, updated, or deleted.
      - Report progress and errors through the UI.
      - Populate ctx["changed_files"] so that downstream Review/Validate phases know what to inspect.
    """

    @property
    def name(self) -> str:
        return "Coding Phase"

    async def run(self, ctx: Dict[str, Any]) -> None:
        steps = ctx["steps"]
        files_to_send = ctx["files"]
        user_task = ctx["user_task"]

        # Process each step (first pass)
        completed_steps: List[int] = []
        changed_files: Set[str] = set()
        failed_steps = []
        for i, step in enumerate(steps["steps"]):
            print_steps(self.app, steps, completed_steps, current_step=i)
            self.app.ui.print_text(
                f"Working on step {i + 1}: {step.get('operation_type')} for {step.get('filename')}",
                PrintType.PROCESSING,
            )

            coding_files = list(files_to_send)  # Start with the initial context files
            for file in changed_files:  # Add any files already modified in this run
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
            self.app.ui.print_text(f"Retrying step {idx + 1}", PrintType.WARNING)
            print_steps(self.app, steps, completed_steps, current_step=idx)
            new_changes = await self.complete_step(step, user_task, files_to_send)
            if new_changes:
                completed_steps.append(idx)
                changed_files.update(new_changes)

        print_steps(self.app, steps, completed_steps)
        ctx["changed_files"] = changed_files

    async def _handle_delete(self, step: Dict) -> List[str]:
        filename = step.get("filename")
        if not filename:
            self.app.ui.print_text("DELETE step missing filename", PrintType.ERROR)
            return []

        try:
            # Use delete_with_confirmation function
            response, _ = await delete_with_confirmation(self.app, filename)
            if response == "yes":
                return [filename]  # File was successfully deleted

            # User cancelled deletion - track this separately and return special marker
            self.agent.user_cancelled_deletions.append(filename)
            return ["__STEP_CANCELLED_BY_USER__"]  # Signals success but no files changed
        except Exception as e:
            self.app.ui.print_text(f"Failed to delete file {filename}: {str(e)}", PrintType.ERROR)
            return []

    async def complete_step(
        self, step: Dict, user_task: str, files_to_send: List[str], retry_message: str = ""
    ) -> List[str]:
        """
        Process an individual step:
          - Obtain the current file content.
          - Request a code change from the LLM.
          - Attempt to apply the change.
          - If the change isn’t accepted, optionally retry.
        Returns a list of files changed or an empty list if the step failed.
        """
        op_type = step.get("operation_type", "").upper()

        # Handle DELETE operations specially - skip AI model and prompt user directly
        if op_type == "DELETE":
            return await self._handle_delete(step)

        # Handle all other operations (existing logic)
        self.app.logger.info(f"complete_step: sending with files: {str(files_to_send)}")

        file_content = get_file_contents(files_to_send)
        code_response = await self.request_code(
            change_instruction=step, user_task=user_task, file_content=file_content, additional_prompt=retry_message
        )
        try:
            result = await self.check_and_apply_code_changes(code_response)
            if result.get("success"):
                return result.get("files_changed", [])
            if "change_requested" in result:
                # Use change-request feedback to retry the step.
                retry_message = result["change_requested"]
                self.app.ui.print_text("Retrying step with additional feedback...", PrintType.WARNING)
                return await self.complete_step(step, user_task, files_to_send, retry_message)
            self.app.logger.error(f"Failed to apply code changes in step. change_requested not in result: {result}")
            return []
        except CodeTaskCancelled as e:
            self.app.ui.print_text(f"Code task cancelled by user: {str(e)}", PrintType.WARNING)
            raise
        except CancelledError:
            self.app.logger.info("complete_step: Worker cancelled")
            raise
        except Exception as e:
            self.app.ui.print_text(f"Step failed: {str(e)}", PrintType.ERROR)
            return []

    def _construct_prompt(
        self, change_instruction: Dict, user_task: str, additional_prompt: str
    ) -> Tuple[str, str, str]:
        op_type: str = change_instruction.get("operation_type", "")
        if not op_type:
            self.app.logger.error(f"_construct_prompt: No operation type: {change_instruction}")
            raise KeyError("operation_type")
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
            self.app.logger.error(f"{error_msg}\n {change_instruction}")
            raise KeyError(error_msg)

        prompt = (
            f"You have been tasked with using the {op_type} operation to {description}. This should be "
            f"applied to the supplied file {filename} and you will need to locate the proper location in "
            f"the code to apply this change. The target location is {location}. "
            "Operations should only be applied to this location, or else the task will fail."
        )
        if additional_prompt:
            prompt = f"{prompt} {additional_prompt}"

        return prompt, dev_msg, op_type

    async def request_code(
        self, change_instruction: Dict, user_task: str, file_content: str, additional_prompt: str = ""
    ) -> str:
        """
        Construct and send a code change request.
        Uses an operation-specific prompt (loaded from a markdown file) and a template prompt.
        """
        prompt, dev_msg, op_type = self._construct_prompt(change_instruction, user_task, additional_prompt)

        # Use MessageBuilder to construct messages
        builder = MessageBuilder(self.app)
        builder.start_user_section()
        builder.add_system_message(dev_msg)
        builder.append_to_user_section(file_content)
        builder.append_to_user_section(prompt)
        messages = builder.build()

        # Send request
        model = self.agent.profile_manager.get_model("advanced_coding")
        self.app.logger.info(f"Sending code request to {model}")
        self.app.ui.print_text(
            f"\nSending code request to {model} (advanced_coding profile)...\n", PrintType.PROCESSING
        )

        sub_task_str = None
        if self.agent.worker_id:
            # create a sub task id
            self.agent.sub_task_count += 1
            sub_task_str = f"{self.agent.worker_id}:{self.agent.sub_task_count }"
            self.app.ui.update_task_info(
                self.agent.worker_id, update={"new_sub_task": sub_task_str, "description": op_type}
            )

        response = await generate_llm_response(
            self.app, model, messages, task_id=sub_task_str, print_stream=True, json_output=True
        )

        # mark sub_task complete
        if self.agent.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        return response

    async def check_and_apply_code_changes(self, response_text: str) -> Dict:
        """
        Extract and parse the JSON snippet for code changes from the LLM response,
        then apply the file changes.
        If the user cancels the code task (selects 'no'), the code task is ended immediately.
        """
        json_block = ""
        try:
            json_block = cutoff_string(response_text, "```json", "```")
            changes = json.loads(json_block)
        except Exception as e:
            self.app.logger.error(f"check_and_apply_code_changes: Parsing json failed: {str(e)}\n Blob:{json_block}")
            raise ValueError() from e

        if "cancel_step" in changes:
            # AI model has determined this step is already completed
            reason = changes["cancel_step"]
            self.app.logger.warning(f"Model determined step was already complete. Reason:{reason}")
            return {"success": True, "cancel_step": True, "files_changed": []}
        if "changes" in changes:
            try:
                # Pass self (Agent instance) to manage accept_all state
                return await apply_file_changes(self.app, changes, self.agent)
            except CodeTaskCancelled as e:
                # User selected 'no' during confirmation, end code task immediately
                self.app.logger.warning(f"Code task cancelled by user: {str(e)}")
                raise
        return {"success": False}
