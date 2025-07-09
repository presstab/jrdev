import json
import os
from typing import Any, Dict, List

from jrdev.agents.pipeline.stage import Stage
from jrdev.core.exceptions import CodeTaskCancelled, Reprompt
from jrdev.file_operations.file_utils import cutoff_string
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class PlanPhase(Stage):
    """
    Generate an actionable plan for code changes and involve the user in its review.

    Responsibilities:
      - Bundle up the current context (task + requested files) and ask the LLM to produce
        a JSON‐formatted sequence of steps ("plan") for modifying those files.
      - Parse and validate the LLM’s response, ensuring each step references an available file.
      - Interactively present the plan to the user, allowing them to:
          • accept the plan as-is
          • accept all future plans automatically
          • edit the plan
          • cancel the operation
          • reprompt the LLM for a new or refined plan
      - Propagate the final, user-approved plan downstream for execution.
    """

    @property
    def name(self) -> str:
        return "Plan Steps"

    async def run(self, ctx: Dict[str, Any]) -> None:
        await self.create_plan(ctx)

    async def create_plan(self, ctx: Dict[str, Any]) -> None:
        files_to_send = ctx["files"]
        user_task = ctx["user_task"]

        # Send requested files and request STEPS to be created
        file_response = await self.request_step_plan(files_to_send, user_task)
        steps = None
        try:
            steps = await self.parse_steps(file_response, files_to_send)
            if "steps" not in steps or not steps["steps"]:
                self.app.logger.error(f"create_plan: malformed steps: {steps}")
                raise TypeError("steps")
        except (json.JSONDecodeError, KeyError) as e:
            self.app.logger.error(f"Failed to parse steps\nerr: {e}\nsteps:\n{file_response}")
            raise

        # Prompt user to accept or edit steps, unless accept_all is active
        if self.agent.accept_all_active:
            self.app.ui.print_text("Accept All is active, skipping steps confirmation.", PrintType.WARNING)
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
                self.agent.accept_all_active = True
                # Proceed as if accepted
            elif user_choice == "cancel":
                raise CodeTaskCancelled()
            elif user_choice == "reprompt":
                additional_prompt = user_result.get("prompt")
                raise Reprompt(additional_prompt)
            else:  # Handle unexpected choice
                self.app.logger.error(f"Unexpected choice from prompt_steps: {user_choice}")
                raise TypeError("prompt_steps")
        ctx["steps"] = steps

    async def request_step_plan(self, files_to_send: List[str], user_task: str) -> str:
        """
        When the initial request detects file changes,
        send the content of those files along with the task details back to the LLM.
        """
        builder = MessageBuilder(self.app)
        builder.start_user_section()

        # Add file contents
        for file in files_to_send:
            builder.add_file(file)

        builder.load_user_prompt("create_steps")
        builder.append_to_user_section(f"**Task**: {user_task}")
        messages = builder.build()

        model = self.agent.profile_manager.get_model("advanced_reasoning")
        self.app.logger.info(f"Sending file contents to {model}")
        self.app.ui.print_text(
            f"\nSending requested files to {model} (advanced_reasoning profile)...", PrintType.PROCESSING
        )

        sub_task_str = None
        if self.agent.worker_id:
            # create a sub task id
            self.agent.sub_task_count += 1
            sub_task_str = f"{self.agent.worker_id}:{self.agent.sub_task_count}"
            self.app.ui.update_task_info(
                self.agent.worker_id, update={"new_sub_task": sub_task_str, "description": "create plan"}
            )

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str)

        # mark sub_task complete
        if self.agent.worker_id:
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
