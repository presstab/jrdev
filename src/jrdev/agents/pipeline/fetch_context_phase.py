import json
import os
from typing import Any, Dict, List

from jrdev.agents.pipeline.stage import Stage
from jrdev.file_operations.file_utils import cutoff_string, requested_files
from jrdev.messages.message_builder import MessageBuilder
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType


class FetchContextPhase(Stage):
    """
    Process the LLM’s initial file request response, prompt LLM for further file requests.
        - If the response includes file requests, this triggers the file request workflow.
            - If the response is malformed, send response out to a different LLM to attempt to salvage it.
        - Send an additional file read request with all current context. This is an expensive double check for time
          and tokens, but does lower failure rates, especially with less sophisticated AI models.
        - Cache all context files locally, as these are the files that may be changed during this agent flow.
            - This provides the ability to generate diffs
    """

    @property
    def name(self) -> str:
        return "Fetch Context"

    async def run(self, ctx: Dict[str, Any]) -> None:
        file_list = await self.process_file_request(ctx)
        ctx["files"] = file_list

    async def process_file_request(self, ctx: Dict[str, Any]) -> List[str]:
        user_task = ctx["user_task"]
        raw_file_request = ctx["file_request"]
        files_to_send = requested_files(raw_file_request)
        if not files_to_send:
            # use a fast model to parse response and see if it is salvageable
            salvaged_response = await self.salvage_get_files(raw_file_request)
            files_to_send = requested_files(salvaged_response)
            if not files_to_send and not self.agent.user_context:
                self.app.logger.error("process_file_request: failed to salvage get_files response\n:%s", files_to_send)
                raise ValueError("get_files")
        if self.agent.user_context:
            self.app.logger.info(f"User context added: {self.agent.user_context}")
        for file in self.agent.user_context:
            if file not in files_to_send:
                files_to_send.append(file)
        self.app.logger.info(f"Initial files requested: {files_to_send}")

        # Check that included files are sufficient
        files_to_send = await self.ask_files_sufficient(files_to_send, user_task)

        self.app.logger.info(f"File request detected: {files_to_send}")

        # Store original content of files before any changes
        for filepath_to_store in files_to_send:
            if os.path.exists(filepath_to_store):
                try:
                    with open(filepath_to_store, "r", encoding="utf-8") as f_original:
                        original_content = f_original.read()
                    self.agent.files_original[filepath_to_store] = original_content
                except Exception as e:
                    self.app.logger.warning(
                        f"CodeProcessor: Could not read original content for {filepath_to_store}: {e}"
                    )
                    self.agent.files_original[filepath_to_store] = ""  # Store empty string if reading fails
            else:
                # File might be created by a 'NEW' operation, so its original content is empty
                self.agent.files_original[filepath_to_store] = ""

        return files_to_send

    async def salvage_get_files(self, bad_message: str):
        """
        Occasionally, getfiles will fail because of bad formatting. Attempt to salvage the message.
        """
        builder = MessageBuilder(self.app)
        builder.load_system_prompt("get_files_format")
        prompt = PromptManager().load("files/salvage_files")
        prompt = prompt.replace("MSG_CONTENT", bad_message)
        builder.start_user_section()
        builder.append_to_user_section(prompt)
        builder.add_tree()
        messages = builder.build()

        model = self.agent.profile_manager.get_model("quick_reasoning")
        self.app.logger.info(f"Attempting to reformat file request with {model}")
        self.app.ui.print_text(
            f"\nAttempting to reformat file request with {model} (quick_reasoning profile)...", PrintType.PROCESSING
        )

        sub_task_str = None
        if self.agent.worker_id:
            # create a sub task id
            self.agent.sub_task_count += 1
            sub_task_str = f"{self.agent.worker_id}:{self.agent.sub_task_count}"
            self.app.ui.update_task_info(
                self.agent.worker_id, update={"new_sub_task": sub_task_str, "description": "format file request"}
            )

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str)

        # mark sub_task complete
        if self.agent.worker_id:
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

        model = self.agent.profile_manager.get_model("low_cost_search")
        self.app.logger.info(f"Analyzing if more files are needed, using {model}")
        self.app.ui.print_text(
            f"\nAnalyzing if more files are needed, using {model} (low_cost_search profile)...", PrintType.PROCESSING
        )

        sub_task_str = None
        if self.agent.worker_id:
            # create a sub task id
            self.agent.sub_task_count += 1
            sub_task_str = f"{self.agent.worker_id}:{self.agent.sub_task_count}"
            self.app.ui.update_task_info(
                self.agent.worker_id, update={"new_sub_task": sub_task_str, "description": "files check"}
            )

        response = await generate_llm_response(self.app, model, messages, task_id=sub_task_str)
        self.app.logger.info(f"additional files response:\n {response}")

        # mark sub_task complete
        if self.agent.worker_id:
            self.app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

        json_content = cutoff_string(response, "```json", "```")
        tool_calls = json.loads(json_content)
        try:
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
        except AttributeError as e:
            self.app.logger.error("ask_files_sufficient: malformed additional files response %s", str(e))
            self.app.ui.print_text("ask_files_sufficient response malformed", PrintType.ERROR)
        return files
