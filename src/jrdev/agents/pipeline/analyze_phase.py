from typing import Any, Dict

from jrdev.agents.pipeline.stage import Stage
from jrdev.messages.message_builder import MessageBuilder
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class AnalyzePhase(Stage):
    """
    Kick off the agent pipeline by interpreting the user’s request in the context of the project.

    Responsibilities:
      - Gather all high-level context:
          • Project file index, tree structure, overview and conventions
          • Any snippets the user manually provided via the UI
      - Send an “analyze” prompt to the LLM asking it to determine which files it must read or modify
      - Capture and stash the raw file_request response into ctx["file_request"]
      - Defer actual file fetching to the FetchContextPhase
    """

    @property
    def name(self) -> str:
        return "Analyze Task"

    async def run(self, ctx: Dict[str, Any]) -> None:
        user_task = ctx["user_task"]
        response = await self.send_initial_request(user_task)
        # stash the raw analysis into the shared context
        ctx["file_request"] = response

    async def send_initial_request(self, user_task: str) -> str:
        # Use MessageBuilder for consistent message construction
        builder = MessageBuilder(self.agent.app)
        for file in self.agent.user_context:
            builder.add_file(file)
        builder.start_user_section(f"The user is seeking guidance for this task to complete: {user_task}")
        builder.load_system_prompt("analyze_task_return_getfiles")
        builder.add_project_files()
        builder.finalize_user_section()
        messages = builder.build()

        model_name = self.agent.profile_manager.get_model("advanced_reasoning")
        self.app.ui.print_text(
            f"\n{model_name} is processing the request... (advanced_reasoning profile)", PrintType.PROCESSING
        )
        sub_task_str = None
        if self.agent.worker_id:
            # create a sub task id
            self.agent.sub_task_count += 1
            sub_task_str = f"{self.agent.worker_id}:{self.agent.sub_task_count}"
            self.app.ui.update_task_info(
                self.agent.worker_id, update={"new_sub_task": sub_task_str, "description": "analyze request"}
            )

        # send request
        response = await generate_llm_response(self.app, model_name, messages, task_id=sub_task_str)

        # mark sub_task complete
        if self.agent.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        return response
