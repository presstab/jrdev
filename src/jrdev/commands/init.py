#!/usr/bin/env python3

"""
Init command implementation for the JrDev terminal.
"""
import asyncio
import os
import time
from typing import List, Optional, Any, Dict


from jrdev.file_utils import (
    find_similar_file,
    pair_header_source_files,
    requested_files,
    JRDEV_DIR,
)
from jrdev.llm_requests import stream_request
from jrdev.languages.utils import detect_language, is_headers_language
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.treechart import generate_compact_tree
from jrdev.ui.ui import terminal_print, PrintType


# Create an asyncio lock for safe file access
context_file_lock = asyncio.Lock()


async def get_file_summary(
    terminal: Any,
    file_path: Any,
    additional_context: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Generate a summary of a file using an LLM and store in the ContextManager.

    Args:
        terminal: The JrDevTerminal instance
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
                terminal_print(f"\nFile not found: {file}", PrintType.ERROR)
                return None

        # Use the context manager to generate the context
        file_input = files[0] if len(files) == 1 else files
        file_analysis = await terminal.context_manager.generate_context(
            file_input, terminal, additional_context
        )

        if file_analysis:
            return f"Analysis for: {file_path} : {file_analysis}"
        return None

    except Exception as e:
        terminal_print(f"Error analyzing file {file_path}: {str(e)}", PrintType.ERROR)
        return None


async def handle_init(terminal: Any, args: List[str]) -> None:
    """
    Handle the /init command to generate file tree, analyze files, and create
    project overview.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments
    """
    # Record start time
    start_time = time.time()

    try:
        output_file = f"{JRDEV_DIR}jrdev_filetree.txt"
        if len(args) > 1:
            output_file = args[1]

        # Generate the tree structure using the token-efficient format
        current_dir = os.getcwd()
        tree_output = generate_compact_tree(
            current_dir, output_file, use_gitignore=True
        )

        terminal_print(
            f"File tree generated and saved to {output_file}", PrintType.SUCCESS
        )

        # Extract file paths from tree_output
        tree_files = [
            line.strip()
            for line in tree_output.splitlines()
            if line.strip() and not line.endswith("/")  # Skip directories
        ]

        # Switch the model to deepseek-r1-671b
        #terminal.model = "deepseek-r1-671b"
        terminal.model = "mistral-31-24b"
        terminal_print(f"Model changed to: {terminal.model}", PrintType.INFO)

        # Send the file tree to the LLM with a request for file recommendations
        terminal_print(
            "Waiting for LLM analysis of project tree...", PrintType.PROCESSING
        )

        # Get file recommendation prompt
        file_recommendation_prompt = PromptManager.load("file_recommendation")

        # Get the format explanation from the prompt file
        format_explanation = PromptManager.load("init/filetree_format")

        # Combine prompt with format explanation and tree output
        recommendation_prompt = (
            f"{file_recommendation_prompt}\n\n{format_explanation}\n\n{tree_output}"
        )

        # Get the system prompt to enforce response format
        dev_prompt = PromptManager.load("files/get_files_format")

        # Create a temporary message list to avoid polluting the conversation
        temp_messages = [
            {"role": "system", "content": dev_prompt},
            {"role": "user", "content": recommendation_prompt},
        ]

        # Send the request to the LLM
        try:
            recommendation_response = await stream_request(
                terminal, terminal.model, temp_messages
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
                            terminal_print(
                                f"Failed to find file {file_path}", PrintType.ERROR
                            )

                if not cleaned_file_list:
                    raise FileNotFoundError("No get_files in init request")

                # pair headers and source files if applicable
                if uses_headers:
                    cleaned_file_list = pair_header_source_files(cleaned_file_list)

                # Print the LLM's response
                terminal_print("\nLLM File Recommendations:", PrintType.HEADER)
                terminal_print(cleaned_file_list, PrintType.INFO)

                terminal_print(
                    f"requesting {len(recommended_files)} files", PrintType.PROCESSING
                )

                # Now switch to a different model for file analysis
                terminal.model = "qwen-2.5-qwq-32b"
                terminal_print(
                    f"\nSwitching model to: {terminal.model} for analysis",
                    PrintType.INFO,
                )

                # Process all recommended files concurrently
                terminal_print(
                    f"\nAnalyzing {len(cleaned_file_list)} files concurrently...",
                    PrintType.PROCESSING,
                )

                async def analyze_file(index: int, file_path: str) -> Optional[str]:
                    """Helper function to analyze a single file."""
                    # prevent rate limits
                    if index > 0 and index % 5 == 0:
                        await asyncio.sleep(2)  # Sleep for 1.5 second

                    terminal_print(
                        f"Starting analysis for file {index + 1}/"
                        f"{len(cleaned_file_list)}: {file_path}",
                        PrintType.PROCESSING,
                    )
                    result = await get_file_summary(terminal, file_path)
                    terminal_print(
                        f"Completed analysis for file {index + 1}/"
                        f"{len(cleaned_file_list)}: {file_path}",
                        PrintType.SUCCESS,
                    )
                    return result

                # Parallel task to generate conventions using the same files
                async def generate_conventions() -> Optional[str]:
                    """Generate project conventions in parallel with file analysis."""
                    terminal_print(
                        f"\nAnalyzing project conventions...", PrintType.PROCESSING
                    )

                    # Use a local model variable instead of changing terminal.model
                    conventions_model = "deepseek-r1-671b"

                    # Get project conventions prompt
                    conventions_prompt = PromptManager.load("project_conventions")

                    # Read the actual content of all files from the tree
                    files_content = []
                    for file_path in tree_files:
                        try:
                            full_path = os.path.join(current_dir, file_path)
                            if os.path.exists(full_path):
                                with open(full_path, "r") as f:
                                    content = f.read()
                                    # Limit file size like in get_file_summary
                                    if len(content) <= 1000 * 1024:
                                        files_content.append(
                                            f"## {file_path}\n\n{content}\n"
                                        )
                        except Exception as e:
                            terminal_print(
                                f"Error reading file {file_path}: {str(e)}",
                                PrintType.ERROR,
                            )

                    # Create conventions messages with file tree and actual file contents
                    conventions_messages = [
                        {"role": "system", "content": conventions_prompt},
                        {
                            "role": "user",
                            "content": (
                                f"FILE TREE:\n{tree_output}\n\n"
                                f"FILE CONTENTS:\n{''.join(files_content)}"
                            ),
                        },
                    ]

                    try:
                        # Use conventions_model directly instead of changing terminal.model
                        conventions_result = await stream_request(
                            terminal,
                            conventions_model,
                            conventions_messages,
                            print_stream=False,
                        )

                        # Save to markdown file
                        conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
                        with open(conventions_file_path, "w") as f:
                            f.write(conventions_result)

                        return conventions_result
                    except Exception as e:
                        terminal_print(
                            f"Error generating project conventions: {str(e)}",
                            PrintType.ERROR,
                        )
                        return None

                # Create a task for generating conventions in parallel
                conventions_task = asyncio.create_task(generate_conventions())

                # Start file analysis tasks
                file_analysis_tasks = [
                    analyze_file(i, file_path)
                    for i, file_path in enumerate(cleaned_file_list)
                ]

                # Wait for all tasks to complete
                results = await asyncio.gather(conventions_task, *file_analysis_tasks)

                # First result is from conventions_task, rest are from file analysis
                conventions_result = results[0]
                file_analysis_results = results[1:]

                # Filter out None results from file analysis
                returned_analysis = [
                    result for result in file_analysis_results if result
                ]

                terminal_print(
                    f"\nCompleted analysis of all {len(returned_analysis)} files",
                    PrintType.SUCCESS,
                )

                # Print conventions if they were generated successfully
                conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
                if conventions_result and os.path.exists(conventions_file_path):
                    terminal_print("\nProject Conventions Analysis:", PrintType.HEADER)
                    terminal_print(conventions_result, PrintType.INFO)

                    terminal_print(
                        f"\nProject conventions generated and saved to "
                        f"{conventions_file_path}",
                        PrintType.SUCCESS,
                    )

                # Start project overview immediately
                terminal_print("\nGenerating project overview...", PrintType.PROCESSING)
                terminal.model = "deepseek-r1-671b"

                # Read the file tree
                with open(output_file, "r") as f:
                    file_tree_content = f.read()

                # Get all file contexts from the context manager
                file_context_content = terminal.context_manager.get_all_context()

                # Get project overview prompt
                system_prompt = PromptManager.load("project_overview")

                # Create the overview prompt
                overview_prompt = (
                    f"FILE TREE:\n{file_tree_content}\n\n"
                    f"FILE CONTEXT:\n{file_context_content}\n\n"
                    f"PROJECT CONVENTIONS:\n{conventions_result}"
                )

                # Send request to the model for project overview
                try:
                    overview_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": overview_prompt},
                    ]
                    full_overview = await stream_request(
                        terminal, terminal.model, overview_messages
                    )

                    # Save to markdown file
                    overview_file_path = f"{JRDEV_DIR}jrdev_overview.md"
                    with open(overview_file_path, "w") as f:
                        f.write(full_overview)

                    terminal_print(
                        f"\nProject overview generated and saved to "
                        f"{overview_file_path}",
                        PrintType.SUCCESS,
                    )
                except Exception as e:
                    terminal_print(
                        f"Error generating project overview: {str(e)}", PrintType.ERROR
                    )

                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                minutes, seconds = divmod(elapsed_time, 60)

                terminal_print(
                    f"\nProject initialization finished (took {int(minutes)}m {int(seconds)}s)",
                    PrintType.SUCCESS,
                )
            except Exception as e:
                terminal_print(
                    f"Error processing file recommendations: {str(e)}", PrintType.ERROR
                )
        except Exception as e:
            terminal_print(
                f"Error getting LLM recommendations: {str(e)}", PrintType.ERROR
            )
    except Exception as e:
        terminal_print(f"Error generating file tree: {str(e)}", PrintType.ERROR)
