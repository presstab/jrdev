from typing import Any, Dict, Set

from jrdev.agents.pipeline.stage import Stage
from jrdev.file_operations.file_utils import get_file_contents
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class ValidatePhase(Stage):
    """
    Ensure that all LLM-generated file edits are well-formed and free of errors.

    Responsibilities:
      - Collect the set of files that were modified during execution.
      - Read their current contents off disk.
      - Send those contents to the LLM with a “validator” system prompt.
      - Parse the LLM’s response (looking for “VALID” vs “INVALID”).
      - Surface a clear pass/fail status (and any error reason) to the user/UI.

    This step runs only once, at the end of the pipeline, to catch any malformed
    code before finalizing the task.
    """

    @property
    def name(self) -> str:
        return "Validate Changes"

    async def run(self, ctx: Dict[str, Any]) -> None:
        # only perform validation once
        changed_files = ctx["changed_files"]
        if not self.agent.files_validated:
            await self.validate_changed_files(changed_files)
            self.agent.files_validated = True

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
        model = self.agent.profile_manager.get_model("intermediate_reasoning")
        self.app.logger.info(f"Validating changed files with {model}")
        self.app.ui.print_text(
            f"\nValidating changed files with {model} (intermediate_reasoning profile)", PrintType.PROCESSING
        )

        sub_task_str = None
        if self.agent.worker_id:
            # create a sub task id
            self.agent.sub_task_count += 1
            sub_task_str = f"{self.agent.worker_id}:{self.agent.sub_task_count}"
            self.app.ui.update_task_info(
                self.agent.worker_id, update={"new_sub_task": sub_task_str, "description": "validate"}
            )

        validation_response = await generate_llm_response(
            self.app, model, messages, task_id=sub_task_str, print_stream=False
        )

        # mark sub_task complete
        if self.agent.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        self.app.logger.info(f"Validation response: {validation_response}")
        if validation_response.strip().startswith("VALID"):
            self.app.ui.print_text("✓ Files validated successfully", PrintType.SUCCESS)
        elif "INVALID" in validation_response:
            reason = (
                validation_response.split("INVALID:")[1].strip() if ":" in validation_response else "Unspecified error"
            )
            self.app.ui.print_text(f"⚠ Files may be malformed: {reason}", PrintType.ERROR)
        else:
            self.app.ui.print_text("⚠ Could not determine file validation status", PrintType.ERROR)
