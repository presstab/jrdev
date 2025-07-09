import json
import os
from difflib import unified_diff
from typing import Any, Dict, List, Set

from jrdev.agents.pipeline.stage import Stage
from jrdev.file_operations.file_utils import cutoff_string
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class ReviewPhase(Stage):
    """
    Compare the LLM’s edits against the user’s request and decide if further changes are needed.

    Responsibilities:
      - Compute unified diffs for every file that was added, modified, or deleted.
      - Annotate any user-cancelled delete operations as “complete.”
      - Assemble diffs, the original user prompt, and the latest file contents into a
        “review_changes” system prompt.
      - Invoke the LLM to produce a JSON review object containing:
          • success (bool)
          • reason (str, when success is False)
          • action (str, recommended next steps)
      - If the review fails (success=False), automatically feed the “action” back into the
        pipeline by re-invoking the agent on that corrective instruction.
      - Otherwise, pass control onward to the final validation phase.

    This phase enforces that the code edits truly fulfill the user’s intent before validating syntax/format.
    """

    @property
    def name(self) -> str:
        return "Review Changes"

    async def run(self, ctx: Dict[str, Any]) -> None:
        changed_files = ctx["changed_files"]
        user_task = ctx["user_task"]
        files_to_send = ctx["files"]
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
                    change_request = (
                        f"The user requested changes and an attempt was made to fulfill the change request. The "
                        f"reviewer determined that the changes failed because {reason}. The reviewer requests that "
                        f"this action be taken to complete the task: {action}. This is the user task: {user_task}"
                    )
                    await self.agent.process(change_request)
                else:
                    self.app.logger.info(f"Malformed change request from reviewer:\n{review}")

        except Exception as e:
            self.app.logger.error(f"err({e}). failed to parse review: {review_response}")

    def _collect_diffs(self, changed_files: Set[str]) -> List[str]:
        all_diff_texts = []

        # Add information about user-cancelled deletions
        for cancelled_file in self.agent.user_cancelled_deletions:
            all_diff_texts.append(
                f"--- DELETE Operation Cancelled by User: {cancelled_file} This part of the task is now completed ---\n"
            )

        for filepath in changed_files:
            # Skip special marker for user-cancelled DELETE operations
            if filepath == "__STEP_CANCELLED_BY_USER__":
                continue

            original_content_str = self.agent.files_original.get(filepath, "")

            # Check if file was deleted (existed originally but doesn't exist now)
            if original_content_str and not os.path.exists(filepath):
                # File was deleted - add a simple formatted line instead of generating diff
                all_diff_texts.append(f"--- File Deleted: {filepath} ---\n")
                continue

            current_content_str = ""
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f_current:
                        current_content_str = f_current.read()
                except Exception as e:
                    self.app.logger.warning(
                        f"CodeProcessor: Could not read current content for {filepath} during review: {e}"
                    )

            original_lines = original_content_str.splitlines(True)
            current_lines = current_content_str.splitlines(True)

            # Generate diff if there are any changes or if it's a new file
            if original_lines != current_lines:
                diff_output = list(
                    unified_diff(original_lines, current_lines, fromfile=f"a/{filepath}", tofile=f"b/{filepath}", n=3)
                )

                if diff_output:  # Ensure diff is not empty
                    diff_text_for_file = "".join(diff_output)
                    all_diff_texts.append(f"--- Diff for {filepath} ---\n{diff_text_for_file}\n")

        return all_diff_texts

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
            # Skip special markers that aren't real file paths
            if filepath_changed == "__STEP_CANCELLED_BY_USER__":
                continue
            if filepath_changed not in full_file_list_for_context:
                full_file_list_for_context.append(filepath_changed)

        builder = MessageBuilder(self.app)
        builder.load_system_prompt("review_changes")

        all_diff_texts = self._collect_diffs(changed_files)
        if all_diff_texts:
            full_diffs_report = "\n".join(all_diff_texts)
            builder.append_to_user_section(f"\n\n**Summary of Changes Made (Diffs):**\n{full_diffs_report}")
            self.app.logger.info(f"{full_diffs_report}")

        builder.append_to_user_section(f"***User Request***: {initial_prompt}")
        for file_for_context in full_file_list_for_context:
            builder.add_file(file_for_context)  # This adds current content of files for LLM context

        messages = builder.build()

        # Validation Model
        model = self.agent.profile_manager.get_model("advanced_reasoning")
        self.app.logger.info(f"Checking work: {model}")
        self.app.ui.print_text(
            f"\nChecking code changes to ensure completion with {model} (advanced_reasoning profile)",
            PrintType.PROCESSING,
        )

        sub_task_str = None
        if self.agent.worker_id:
            # create a sub task id
            self.agent.sub_task_count += 1
            sub_task_str = f"{self.agent.worker_id}:{self.agent.sub_task_count}"
            self.app.ui.update_task_info(
                self.agent.worker_id, update={"new_sub_task": sub_task_str, "description": "check work"}
            )

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str, print_stream=False)

        # mark sub_task complete
        if self.agent.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})
        self.app.ui.print_text(f"Check Work:\n {response}", PrintType.PROCESSING)

        return response
