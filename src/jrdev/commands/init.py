#!/usr/bin/env python3

"""
Init command implementation for the JrDev application.
"""
import asyncio
import os
import time
from typing import List, Optional, Any

from jrdev.file_operations.file_utils import (
    find_similar_file,
    pair_header_source_files,
    requested_files,
    JRDEV_DIR,
    write_string_to_file,  # Import the function
)
from jrdev.services.llm_requests import generate_llm_response
from jrdev.languages.utils import detect_language, is_headers_language
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.utils.string_utils import contains_chinese
from jrdev.ui.ui import PrintType
from jrdev.messages.message_builder import MessageBuilder

# Create an asyncio lock for safe file access
context_file_lock = asyncio.Lock()


async def get_file_summary(
    app: Any,
    file_path: Any,
    additional_context: Optional[List[str]] = None,
    task_id: Optional[str] = None
) -> Optional[str]:
    """
    Generate a summary of a file using an LLM and store in the ContextManager.

    Args:
        app: The Application instance
        file_path: Path to the file to analyze. This may also be a list of file paths
        additional_context: Optional additional context for the LLM

    Returns:
        Optional[str]: File analysis or None if an error occurred
    """
    if additional_context is None:
        additional_context = []
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
            file_input, app, additional_context=additional_context, task_id=task_id
        )

        if file_analysis:
            return f"{file_analysis}"
        return None

    except Exception as e:
        app.ui.print_text(f"Error analyzing file {file_path}: {str(e)}", PrintType.ERROR)
        return None


async def handle_init(app: Any, args: List[str], worker_id: str) -> None:
    """
    Handle the /init command to generate file tree, analyze files, and create
    project overview.

    Args:
        app: The Application instance
        args: Command arguments
    """
    # Record start time
    start_time = time.time()

    # Initialize the profile manager once for the entire function
    profile_manager = app.profile_manager()

    try:
        # Generate the tree structure using the token-efficient format
        current_dir = os.getcwd()
        tree_output = app.get_file_tree()

        # Switch the model to the advanced reasoning profile
        app.state.model = profile_manager.get_model("advanced_reasoning")
        app.ui.print_text(f"Model changed to: {app.state.model} (advanced_reasoning profile)", PrintType.INFO)

        # Send the file tree to the LLM with a request for file recommendations
        app.ui.print_text("Waiting for LLM analysis of project tree...", PrintType.PROCESSING)

        # Use MessageBuilder for file recommendations
        builder = MessageBuilder(app)
        builder.load_system_prompt("files/get_files_format")
        
        # Start user section with file recommendation prompt
        builder.start_user_section()
        builder.append_to_user_section(PromptManager.load("file_recommendation"))
        builder.append_to_user_section(PromptManager.load("init/filetree_format"))
        builder.append_to_user_section(tree_output)
        builder.finalize_user_section()
        
        # Get the constructed message list
        temp_messages = builder.build()

        # Send the request to the LLM
        sub_task_id = 0
        try:
            recommendation_response = await generate_llm_response(
                app, app.state.model, temp_messages, task_id=worker_id
            )

            # Parse the file list from the response
            try:
                recommended_files = requested_files(recommendation_response)

                # Check that each file exists
                cleaned_file_list = []
                uses_headers = False
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
                        else:
                            app.ui.print_text(
                                f"Failed to find file {file_path}", PrintType.ERROR
                            )

                if not cleaned_file_list:
                    raise FileNotFoundError("No get_files in init request")

                # pair headers and source files if applicable
                if uses_headers:
                    cleaned_file_list = pair_header_source_files(cleaned_file_list)

                # Print the LLM's response
                app.ui.print_text("\nLLM File Recommendations:", PrintType.HEADER)
                app.ui.print_text(str(cleaned_file_list), PrintType.INFO)

                app.ui.print_text(
                    f"requesting {len(recommended_files)} files", PrintType.PROCESSING
                )

                # Now switch to a different model for file analysis
                app.state.model = profile_manager.get_model("intermediate_reasoning")
                app.ui.print_text(
                    f"\nSwitching model to: {app.state.model} (intermediate_reasoning profile) for analysis",
                    PrintType.INFO,
                )

                # Process all recommended files concurrently
                app.ui.print_text(
                    f"\nAnalyzing {len(cleaned_file_list)} files concurrently...",
                    PrintType.PROCESSING,
                )

                async def analyze_file(index: int, file_path: str, task_id: str = None) -> Optional[str]:
                    """Helper function to analyze a single file."""
                    # prevent rate limits
                    await asyncio.sleep(index)

                    sub_task_str = None
                    if task_id:
                        # create a sub task id
                        sub_task_str = f"{task_id}:{index}"
                        app.ui.update_task_info(task_id, update={"new_sub_task": sub_task_str, "description": str(file_path)})

                    app.ui.print_text(
                        f"Starting analysis for file {index + 1}/"
                        f"{len(cleaned_file_list)}: {file_path}",
                        PrintType.PROCESSING,
                    )

                    result = await get_file_summary(app, file_path, task_id=sub_task_str)
                    app.ui.print_text(
                        f"Completed analysis for file {index + 1}/"
                        f"{len(cleaned_file_list)}: {file_path}",
                        PrintType.SUCCESS,
                    )

                    # mark sub_task complete
                    if task_id:
                        sub_task_str = f"{task_id}:{index}"
                        app.ui.update_task_info(sub_task_str, update={"sub_task_finished": True})

                    return result

                # Parallel task to generate conventions using the same files
                async def generate_conventions() -> Optional[str]:
                    """Generate project conventions in parallel with file analysis."""
                    app.ui.print_text(
                        f"\nAnalyzing project conventions...", PrintType.PROCESSING
                    )

                    # Use a local model variable from profile instead of changing app.state.model
                    conventions_model = profile_manager.get_model("advanced_reasoning")

                    # Use MessageBuilder for conventions
                    conventions_builder = MessageBuilder(app)
                    conventions_builder.load_system_prompt("project_conventions")
                    conventions_builder.add_tree()
                    for idx, file in enumerate(cleaned_file_list):
                        # limit the amount sent
                        if idx < 7:
                            #possible this is a list of files not a file
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
                    conventions_task_id = None
                    if worker_id:
                        conventions_task_id = f"{worker_id}:{len(cleaned_file_list)}"
                        app.ui.update_task_info(worker_id, update={"new_sub_task": conventions_task_id, "description": "Project Conventions"})

                    try:
                        # Use conventions_model directly instead of changing app.state.model
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

                # Create a task for generating conventions in parallel
                conventions_task = asyncio.create_task(generate_conventions())

                # Start file analysis tasks
                file_analysis_tasks = [
                    analyze_file(i, file_path, worker_id)
                    for i, file_path in enumerate(cleaned_file_list)
                ]

                # Wait for all tasks to complete
                results = await asyncio.gather(conventions_task, *file_analysis_tasks)

                # First result is from conventions_task, rest are from file analysis
                conventions_result = results[0]
                file_analysis_results = results[1:]

                # Filter out None results and those containing Chinese characters
                returned_analysis = []
                for result in file_analysis_results:
                    if result is not None and not contains_chinese(result):
                        returned_analysis.append(result)

                app.ui.print_text(
                    f"\nCompleted analysis of all {len(returned_analysis)} files",
                    PrintType.SUCCESS,
                )

                # Check if conventions were generated successfully
                conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
                if conventions_result is None or not os.path.exists(conventions_file_path):
                    app.ui.print_text(
                        "\nError: Project conventions generation failed. Please try running /init again.",
                        PrintType.ERROR
                    )
                    # Calculate elapsed time before exiting
                    elapsed_time = time.time() - start_time
                    minutes, seconds = divmod(elapsed_time, 60)
                    app.ui.print_text(
                        f"\nProject initialization failed (took {int(minutes)}m {int(seconds)}s)",
                        PrintType.ERROR,
                    )
                    return

                # Print conventions
                app.ui.print_text("\nProject Conventions Analysis:", PrintType.HEADER)
                app.ui.print_text(conventions_result, PrintType.INFO)

                app.ui.print_text(
                    f"\nProject conventions generated and saved to "
                    f"{conventions_file_path}",
                    PrintType.SUCCESS,
                )

                # Start project overview
                app.ui.print_text("\nGenerating project overview...", PrintType.PROCESSING)
                app.state.model = profile_manager.get_model("advanced_reasoning")

                # Use the tree output directly instead of reading from a file
                file_tree_content = tree_output

                # Get all file contexts from the context manager
                file_context_content = app.context_manager.get_all_context()

                # Use MessageBuilder for project overview
                overview_builder = MessageBuilder(app)
                overview_builder.load_system_prompt("project_overview")
                
                # Create the overview prompt with multiple sections
                overview_builder.start_user_section("FILE TREE:\n")
                overview_builder.append_to_user_section(file_tree_content)
                overview_builder.append_to_user_section("\n\nFILE CONTEXT:\n")
                overview_builder.append_to_user_section(file_context_content)
                overview_builder.append_to_user_section("\n\nPROJECT CONVENTIONS:\n")
                overview_builder.append_to_user_section(conventions_result)
                overview_builder.finalize_user_section()
                
                # Get the constructed message list
                overview_messages = overview_builder.build()

                # Create a sub task id for project overview
                overview_task_id = None
                if worker_id:
                    overview_task_id = f"{worker_id}:{len(cleaned_file_list) + 1}"
                    app.ui.update_task_info(worker_id, update={"new_sub_task": overview_task_id, "description": "Project Overview"})
                
                # Send request to the model for project overview
                try:
                    full_overview = await generate_llm_response(
                        app, app.state.model, overview_messages, task_id=overview_task_id
                    )

                    # Save to markdown file
                    overview_file_path = f"{JRDEV_DIR}jrdev_overview.md"
                    write_string_to_file(overview_file_path, full_overview)

                    app.ui.print_text(
                        f"\nProject overview generated and saved to "
                        f"{overview_file_path}",
                        PrintType.SUCCESS,
                    )

                    # Mark overview sub_task complete
                    if overview_task_id:
                        app.ui.update_task_info(overview_task_id, update={"sub_task_finished": True})
                except Exception as e:
                    app.ui.print_text(
                        f"Error generating project overview: {str(e)}", PrintType.ERROR
                    )
                    # Mark overview sub_task as failed if an error occurs
                    if overview_task_id:
                        app.ui.update_task_info(overview_task_id, update={"sub_task_finished": True, "status": "failed"})

                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                minutes, seconds = divmod(elapsed_time, 60)

                app.ui.print_text(
                    f"\nProject initialization finished (took {int(minutes)}m {int(seconds)}s)",
                    PrintType.SUCCESS,
                )
            except Exception as e:
                app.ui.print_text(
                    f"Error processing file recommendations: {str(e)}", PrintType.ERROR
                )
        except Exception as e:
            app.ui.print_text(
                f"Error getting LLM recommendations: {str(e)}", PrintType.ERROR
            )
    except Exception as e:
        app.ui.print_text(f"Error generating file tree: {str(e)}", PrintType.ERROR)
