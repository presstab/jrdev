from typing import Any, Dict, List

from jrdev.agents.pipeline.analyze_phase import AnalyzePhase
from jrdev.agents.pipeline.execute_phase import ExecutePhase
from jrdev.agents.pipeline.fetch_context_phase import FetchContextPhase
from jrdev.agents.pipeline.plan_phase import PlanPhase
from jrdev.agents.pipeline.review_phase import ReviewPhase
from jrdev.agents.pipeline.stage import Stage
from jrdev.agents.pipeline.validate_phase import ValidatePhase
from jrdev.core.exceptions import Reprompt
from jrdev.ui.ui import PrintType


class CodeAgent:
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
        self.accept_all_active = False  # Track if 'Accept All' is active for this instance
        self.files_validated = False
        self.files_original: Dict[str, str] = {}  # Stores original file content: {filepath: content}
        self.user_cancelled_deletions: List[str] = []  # Stores filenames that user chose not to delete

        # get custom user set code context, which should be cleared from app state after fetching
        self.user_context = app.get_code_context()
        app.clear_code_context()

        # build the ordered list of stages
        self.phases: List[Stage] = [
            AnalyzePhase(self),
            FetchContextPhase(self),
            PlanPhase(self),
            ExecutePhase(self),
            ReviewPhase(self),
            ValidatePhase(self),
        ]

    async def process(self, user_task: str) -> None:
        """
        The main orchestration method.
        This method performs:
          1. Sending the initial request (the user’s task with any context)
          2. Interpreting the LLM response to see if file changes are requested
          3. Requesting file content if needed, parsing returned steps, and executing each step
          4. Validating the changed files at the end (only at the top level)
        """
        ctx: Dict[str, Any] = {"user_task": user_task}
        try:
            for phase in self.phases:
                self.app.ui.print_text(f"Starting phase: {phase.name}", print_type=PrintType.PROCESSING)
                await phase.run(ctx)
        except Reprompt as additional_prompt:
            await self.process(f"{user_task} {additional_prompt}")
