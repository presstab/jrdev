import asyncio
import os
from typing import Any, List, Optional

from jrdev.file_operations.file_utils import write_string_to_file  # Import the function
from jrdev.file_operations.file_utils import JRDEV_DIR, find_similar_file, pair_header_source_files, requested_files
from jrdev.languages.utils import detect_language, is_headers_language
from jrdev.messages.message_builder import MessageBuilder
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.services.llm_requests import generate_llm_response
from jrdev.ui.ui import PrintType

# Create an asyncio lock for safe file access
context_file_lock = asyncio.Lock()


async def get_file_summary(app: Any, file_path: Any, task_id: Optional[str] = None) -> Optional[str]:
    """
    Generate a summary of a file using an LLM and store in the ContextManager.

    Args:
        app: The Application instance
        file_path: Path to the file to analyze. This may also be a list of file paths

    Returns:
        Optional[str]: File analysis or None if an error occurred
    """
    current_dir = os.getcwd()

    files = file_path
    if not isinstance(file_path, list):
        files = [file_path]

    # Process the file using the context manager
    try:
        # Convert files to absolute paths if needed
        for file in files:
            full_path = os.path.join(current_dir, file)
            if not os.path.exists(full_path):
                app.ui.print_text(f"\nFile not found: {file}", PrintType.ERROR)
                return None

        # Use the context manager to generate the context
        file_input = files[0] if len(files) == 1 else files
        file_analysis = await app.context_manager.generate_context(
            file_input, app, additional_context=None, task_id=task_id
        )

        if file_analysis:
            return f"{file_analysis}"
        return None

    except Exception as e:
        app.ui.print_text(f"Error analyzing file {file_path}: {str(e)}", PrintType.ERROR)
        return None


async def handle_init(app: Any, _args: List[str], worker_id: str) -> None:
    """
    Initializes JrDev's understanding of the current project.

    This powerful command performs a one-time, comprehensive analysis of the
    project. It scans the file tree, uses an LLM to identify key files,
    generates summaries for them, and creates two crucial context files:
    - `.jrdev/jrdev_conventions.md`: Outlines the project's coding conventions.
    - `.jrdev/jrdev_overview.md`: Provides a high-level architectural overview.
    This process populates the project context, enabling more accurate and
    efficient AI assistance.

    Usage:
      /init
    """
    try:
        # Generate the tree structure using the token-efficient format
        tree_output = app.get_file_tree()

        # Switch the model to the advanced reasoning profile
        model_advanced_reasoning = app.profile_manager().get_model("advanced_reasoning")

        # Send the file tree to the LLM with a request for file recommendations
        app.ui.print_text(
            f"Waiting for LLM analysis of project tree from {model_advanced_reasoning}", PrintType.PROCESSING
        )

        # Use MessageBuilder for file recommendations
        builder = MessageBuilder(app)
        builder.load_system_prompt("files/get_files_format")

        # Start user section with file recommendation prompt
        builder.start_user_section()
        builder.append_to_user_section(PromptManager.load("file_recommendation"))
        builder.append_to_user_section(PromptManager.load("init/filetree_format"))
        builder.append_to_user_section(tree_output)
        builder.finalize_user_section()

        # Send the request to the LLM
        recommendation_response = await generate_llm_response(
            app, model_advanced_reasoning, builder.build(), task_id=worker_id
        )

        # Check that each file exists
        cleaned_file_list = _clean_file_list(requested_files(recommendation_response))

        if not cleaned_file_list:
            raise FileNotFoundError("No get_files in init request")

        # Print the LLM's response
        app.ui.print_text("\nLLM File Recommendations:", PrintType.HEADER)
        app.ui.print_text(str(cleaned_file_list), PrintType.INFO)

        # Process all recommended files concurrently
        app.ui.print_text(
            f"\nAnalyzing {len(cleaned_file_list)} files concurrently...",
            PrintType.PROCESSING,
        )

        # Create a task for generating conventions in parallel
        conventions_task = asyncio.create_task(generate_conventions(app, cleaned_file_list, worker_id))

        # Start file analysis tasks
        file_analysis_tasks = [
            analyze_file(app, i, file_path, cleaned_file_list, worker_id)
            for i, file_path in enumerate(cleaned_file_list)
        ]

        # Wait for all tasks to complete
        results = await asyncio.gather(conventions_task, *file_analysis_tasks)

        # First result is from conventions_task, rest are from file analysis
        conventions_result = results[0]

        # Check if conventions were generated successfully
        conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
        if conventions_result is None or not os.path.exists(conventions_file_path):
            app.ui.print_text(
                "\nError: Project conventions generation failed. Please try running /init again.",
                PrintType.ERROR,
            )
            return

        app.ui.print_text(
            f"\nProject conventions generated and saved to " f"{conventions_file_path}",
            PrintType.SUCCESS,
        )
        await _generate_project_overview(app, tree_output, conventions_result, cleaned_file_list, worker_id)
    except Exception as e:
        app.ui.print_text(f"Error generating file tree: {str(e)}", PrintType.ERROR)


def _clean_file_list(recommended_files) -> List[str]:
    uses_headers = False
    cleaned_file_list = []
    for file_path in recommended_files:
        lang = detect_language(file_path)
        if is_headers_language(lang):
            uses_headers = True

        if os.path.exists(file_path) and os.path.isfile(file_path):
            cleaned_file_list.append(file_path)
        else:
            similar_file = find_similar_file(file_path)
            if similar_file:
                cleaned_file_list.append(similar_file)

    # pair headers and source files if applicable
    if uses_headers:
        cleaned_file_list = pair_header_source_files(cleaned_file_list)

    return cleaned_file_list


async def analyze_file(
    app: Any, index: int, file_path: str, cleaned_file_list: List[str], task_id: str = ""
) -> Optional[str]:
    """Helper function to analyze a single file."""
    # prevent rate limits
    await asyncio.sleep(index)

    sub_task_str = ""
    if task_id:
        # create a sub task id
        sub_task_str = f"{task_id}:{index}"
        app.ui.update_task_info(task_id, update={"new_sub_task": sub_task_str, "description": str(file_path)})

    app.ui.print_text(
        f"Starting analysis for file {index + 1}/{len(cleaned_file_list)}: {file_path}",
        PrintType.PROCESSING,
    )

    result = await get_file_summary(app, file_path, task_id=sub_task_str)
    app.ui.print_text(
        f"Completed analysis for file {index + 1}/{len(cleaned_file_list)}: {file_path}",
        PrintType.SUCCESS,
    )

    # mark sub_task complete
    if task_id:
        sub_task_str = f"{task_id}:{index}"
        app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

    return result


# Parallel task to generate conventions using the same files
async def generate_conventions(app: Any, cleaned_file_list: List[str], worker_id: str) -> Optional[str]:
    """Generate project conventions in parallel with file analysis."""
    app.ui.print_text("\nAnalyzing project conventions...", PrintType.PROCESSING)

    # Use a local model variable from profile instead of changing app.state.model
    conventions_model = app.profile_manager().get_model("advanced_reasoning")

    # Use MessageBuilder for conventions
    conventions_builder = MessageBuilder(app)
    conventions_builder.load_system_prompt("project_conventions")
    conventions_builder.add_tree()
    for idx, file in enumerate(cleaned_file_list):
        # limit the amount sent
        if idx < 7:
            # possible this is a list of files not a file
            if isinstance(file, list):
                for f in file:
                    conventions_builder.add_file(f)
            else:
                conventions_builder.add_file(file)

    # Finalize the user section
    conventions_builder.finalize_user_section()

    # Get the constructed message list
    conventions_messages = conventions_builder.build()

    # Create a sub task id for conventions
    conventions_task_id = ""
    if worker_id:
        conventions_task_id = f"{worker_id}:{len(cleaned_file_list)}"
        app.ui.update_task_info(
            worker_id,
            update={"new_sub_task": conventions_task_id, "description": "Project Conventions"},
        )

    try:
        # Send request
        conventions_result = await generate_llm_response(
            app,
            conventions_model,
            conventions_messages,
            task_id=conventions_task_id,
            print_stream=False,
        )

        # Save to markdown file using the utility function
        conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
        write_string_to_file(conventions_file_path, conventions_result)

        # Mark conventions sub_task complete
        if conventions_task_id:
            app.ui.update_task_info(conventions_task_id, update={"sub_task_finished": True})

        return conventions_result
    except Exception as e:
        app.ui.print_text(
            f"Error generating project conventions: {str(e)}",
            PrintType.ERROR,
        )
        # Mark conventions sub_task as failed if an error occurs
        if conventions_task_id:
            app.ui.update_task_info(conventions_task_id, update={"sub_task_finished": True, "status": "failed"})
        return None


async def _generate_project_overview(
    app: Any, tree_output: str, conventions: str, cleaned_file_list: List[str], worker_id: str
) -> None:
    app.ui.print_text("\nGenerating project overview...", PrintType.PROCESSING)

    # Get all file contexts from the context manager
    file_context_content = app.context_manager.get_all_context()

    # Use MessageBuilder for project overview
    overview_builder = MessageBuilder(app)
    overview_builder.load_system_prompt("project_overview")

    # Create the overview prompt with multiple sections
    overview_builder.start_user_section("FILE TREE:\n")
    overview_builder.append_to_user_section(tree_output)
    overview_builder.append_to_user_section("\n\nFILE CONTEXT:\n")
    overview_builder.append_to_user_section(file_context_content)
    overview_builder.append_to_user_section("\n\nPROJECT CONVENTIONS:\n")
    overview_builder.append_to_user_section(conventions)
    overview_builder.finalize_user_section()

    # Create a sub task id for project overview
    overview_task_id = None
    if worker_id:
        overview_task_id = f"{worker_id}:{len(cleaned_file_list) + 1}"
        app.ui.update_task_info(worker_id, update={"new_sub_task": overview_task_id, "description": "Project Overview"})

    # Send request to the model for project overview
    try:
        model = app.profile_manager().get_model("advanced_reasoning")
        full_overview = await generate_llm_response(app, model, overview_builder.build(), task_id=overview_task_id)

        # Save to markdown file
        overview_file_path = f"{JRDEV_DIR}jrdev_overview.md"
        write_string_to_file(overview_file_path, full_overview)

        app.ui.print_text(
            f"\nProject overview generated and saved to " f"{overview_file_path}",
            PrintType.SUCCESS,
        )

        # Mark overview sub_task complete
        if overview_task_id:
            app.ui.update_task_info(overview_task_id, update={"sub_task_finished": True})
    except Exception as e:
        app.ui.print_text(f"Error generating project overview: {str(e)}", PrintType.ERROR)
        # Mark overview sub_task as failed if an error occurs
        if overview_task_id:
            app.ui.update_task_info(overview_task_id, update={"sub_task_finished": True, "status": "failed"})
