#!/usr/bin/env python3

"""
Init command implementation for the JrDev terminal.
"""
import asyncio
import os
import time
import re # Import the regex module
from typing import List, Optional, Any, Dict, Tuple


from jrdev.file_utils import requested_files, JRDEV_DIR
from jrdev.llm_requests import stream_request
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.treechart import generate_compact_tree
from jrdev.ui.ui import terminal_print, PrintType


# Create an asyncio lock for safe file access
context_file_lock = asyncio.Lock()


async def get_file_summary(
    terminal: Any,
    file_path: str,
    context_file_path: str,
    additional_context: Optional[List[str]] = None
) -> Optional[str]:
    """
    Generate a summary of a file using an LLM.

    Args:
        terminal: The JrDevTerminal instance
        file_path: Path to the file to analyze
        context_file_path: Path to the context file to append analysis
        additional_context: Optional additional context for the LLM

    Returns:
        Optional[str]: File analysis or None if an error occurred
    """
    if additional_context is None:
        additional_context = []
    current_dir = os.getcwd()
    full_path = os.path.join(current_dir, file_path)
    if not os.path.exists(full_path):
        terminal_print(f"\nFile not found: {file_path}", PrintType.ERROR)
        # Update the context file safely with a lock
        async with context_file_lock:
            with open(context_file_path, "a") as context_file:
                context_file.write(f"\n## {file_path}\n\n")
                context_file.write("Error: File not found\n\n")
        return None

    # Read the file content
    try:
        with open(full_path, "r") as f:
            file_content = f.read()

        # Limit file size
        if len(file_content) > 1000*1024:
            terminal_print(
                f"File {full_path} is too large to send",
                PrintType.WARNING
            )
            # Update context file to indicate skipped large file
            async with context_file_lock:
                with open(context_file_path, "a") as context_file:
                    context_file.write(f"\n## {file_path}\n\n")
                    context_file.write(
                        f"Skipped: File too large ({len(file_content)} bytes)\n\n"
                    )
            return None # Return None as analysis wasn't performed

        # Get prompt from the prompt manager
        text_prompt = PromptManager.load("file_analysis")

        # Create a new chat thread for each file
        temp_messages: List[Dict[str, str]] = [
            {"role": "user", "content": file_content},
            {"role": "system", "content": text_prompt}
        ]
        if len(additional_context) > 0:
            temp_messages.append(
                {"role": "assistant", "content": str(additional_context)}
            )

        terminal_print(
            f"Waiting for LLM analysis of {file_path}...",
            PrintType.PROCESSING
        )

        # Send the request to the LLM (no streaming print needed for concurrent)
        file_analysis = await stream_request(
            terminal, terminal.model, temp_messages, print_stream=False
        )

        # Print the analysis after completion
        terminal_print(f"\nFile Analysis for {file_path}:", PrintType.HEADER)
        terminal_print(file_analysis, PrintType.INFO)

        # Update the context file safely with a lock
        async with context_file_lock:
            with open(context_file_path, "a") as context_file:
                context_file.write(f"\n## {file_path}\n\n")
                context_file.write(f"{file_analysis}\n\n")

        terminal_print(
            f"Completed analysis for {file_path}. Results saved to {context_file_path}",
            PrintType.SUCCESS
        )
        # Return a structured result or just the analysis string
        return f"Analysis for: {file_path} : {file_analysis}"

    except Exception as e:
        terminal_print(
            f"Error analyzing file {file_path}: {str(e)}",
            PrintType.ERROR
        )
        # Update the context file safely with a lock
        async with context_file_lock:
            with open(context_file_path, "a") as context_file:
                context_file.write(f"\n## {file_path}\n\n")
                context_file.write(f"Error analyzing file: {str(e)}\n\n")
        return None


async def _generate_file_tree_and_paths(
    args: List[str]
) -> Tuple[str, str, List[str]]:
    """Generates the file tree, saves it, and extracts file paths."""
    output_file = f"{JRDEV_DIR}jrdev_filetree.txt"
    if len(args) > 1:
        output_file = args[1]

    current_dir = os.getcwd()
    try:
        tree_output = generate_compact_tree(
            current_dir, output_file, use_gitignore=True
        )
        terminal_print(
            f"File tree generated and saved to {output_file}",
            PrintType.SUCCESS
        )

        # --- Updated Parsing Logic ---
        tree_files = []
        lines = tree_output.strip().splitlines()
        if not lines or not lines[0].startswith("ROOT="):
            terminal_print("Error: Invalid tree format (ROOT= line missing)", PrintType.ERROR)
            # Decide how to handle this - raise error or return empty? Returning empty for now.
            return output_file, tree_output, []

        # Skip the ROOT= line
        for line in lines[1:]:
            line = line.strip()
            if not line or line.endswith('/'): # Skip empty lines or explicit directories
                continue

            match = re.match(r"^(.*?):\[(.*?)\]$", line)
            if match:
                dir_part = match.group(1)
                files_part = match.group(2)

                # Split files, handling potential spaces if any (though format shouldn't have them)
                files_in_dir = [f.strip() for f in files_part.split(',') if f.strip()]

                for file_name in files_in_dir:
                    if dir_part: # If dir_part is not empty (i.e., not root)
                         # os.path.join handles separators correctly
                        tree_files.append(os.path.join(dir_part, file_name))
                    else: # file is in the root directory
                        tree_files.append(file_name)
            else:
                # Handle potential future formats or errors if needed
                terminal_print(f"Warning: Skipping unparseable line in tree: {line}", PrintType.WARNING)
        # --- End Updated Parsing Logic ---

        return output_file, tree_output, tree_files
    except Exception as e:
        terminal_print(f"Error generating file tree or parsing paths: {str(e)}", PrintType.ERROR)
        raise  # Re-raise to be caught by the main handler


async def _get_file_recommendations(
    terminal: Any, tree_output: str
) -> List[str]:
    """Gets file recommendations from the LLM based on the file tree."""
    original_model = terminal.model # Store original model
    try:
        # Switch the model for recommendation
        terminal.model = "mistral-31-24b"
        terminal_print(f"Model changed to: {terminal.model}", PrintType.INFO)

        terminal_print(
            "Waiting for LLM analysis of project tree...",
            PrintType.PROCESSING
        )

        file_recommendation_prompt = PromptManager.load("file_recommendation")
        format_explanation = PromptManager.load("init/filetree_format")
        dev_prompt = PromptManager.load("files/get_files_format")

        recommendation_prompt = (
            f"{file_recommendation_prompt}\n\n{format_explanation}\n\n{tree_output}"
        )
        temp_messages = [
            {"role": "system", "content": dev_prompt},
            {"role": "user", "content": recommendation_prompt}
        ]

        recommendation_response = await stream_request(
            terminal, terminal.model, temp_messages
        )

        terminal_print("\nLLM File Recommendations:", PrintType.HEADER)
        terminal_print(recommendation_response, PrintType.INFO)

        recommended_files = requested_files(recommendation_response)
        terminal_print(
            f"LLM recommended {len(recommended_files)} files for analysis.",
            PrintType.INFO
        )
        return recommended_files
    except Exception as e:
        terminal_print(
            f"Error getting LLM recommendations: {str(e)}",
            PrintType.ERROR
        )
        raise # Re-raise to be caught by the main handler
    finally:
        terminal.model = original_model # Restore original model


async def _run_analysis_and_conventions(
    terminal: Any,
    recommended_files: List[str],
    tree_files: List[str],
    tree_output: str
) -> Tuple[List[str], Optional[str]]:
    """Runs file analysis and convention generation concurrently."""
    original_model = terminal.model # Store model before analysis
    context_file_path = f"{JRDEV_DIR}jrdev_filecontext.md"
    current_dir = os.getcwd()

    try:
        # Switch model for detailed analysis
        terminal.model = "qwen-2.5-qwq-32b"
        terminal_print(
            f"\nSwitching model to: {terminal.model} for analysis",
            PrintType.INFO
        )

        # Initialize the context file
        with open(context_file_path, "w") as context_file:
            context_file.write("# Project Context Analysis\n\n")
            context_file.write(
                f"Based on LLM recommendation, analyzing {len(recommended_files)} files.\n\n"
            )

        terminal_print(
            f"\nAnalyzing {len(recommended_files)} recommended files and project conventions concurrently...",
            PrintType.PROCESSING
        )

        # --- Nested Helper Functions ---
        async def analyze_file(index: int, file_path: str) -> Optional[str]:
            """Helper function to analyze a single recommended file."""
            # Note: Progress prints are now less critical as get_file_summary prints start/end
            result = await get_file_summary(
                terminal, file_path, context_file_path
            )
            return result

        async def generate_conventions() -> Optional[str]:
            """Generate project conventions in parallel using all tree files."""
            terminal_print(
                f"\nAnalyzing project conventions using {len(tree_files)} files...",
                PrintType.PROCESSING
            )
            conventions_model = "mistral-31-24b" # Keep convention model separate
            conventions_prompt = PromptManager.load("project_conventions")
            files_content = []
            current_dir = os.getcwd() # Ensure current_dir is fresh within this scope

            for file_path in tree_files:
                try:
                    full_path = os.path.join(current_dir, file_path)
                    exists = os.path.exists(full_path)
                    if exists:
                        with open(full_path, "r") as f:
                            content = f.read()
                            content_len = len(content)
                            # Limit file size
                            if content_len > 0 and content_len <= 1000 * 1024: # Added check for > 0
                                files_content.append(f"## {file_path}\n\n{content}\n")
                            elif content_len == 0:
                                terminal_print(f"Skipping empty file {file_path} for conventions analysis.", PrintType.WARNING)
                            else: # File too large
                                terminal_print(f"Skipping large file {file_path} ({content_len} bytes) for conventions analysis.", PrintType.WARNING)
                except Exception as e:
                    terminal_print( # Keep error reporting
                        f"Error reading file {file_path} for conventions: {str(e)}",
                        PrintType.ERROR
                    )

            if not files_content:
                 terminal_print("No files could be read for conventions analysis.", PrintType.WARNING)
                 return None

            conventions_messages = [
                {"role": "system", "content": conventions_prompt},
                {"role": "user", "content": (
                    f"FILE TREE:\n{tree_output}\n\n"
                    f"FILE CONTENTS:\n{''.join(files_content)}"
                )}
            ]

            try:
                conventions_result = await stream_request(
                    terminal, conventions_model, conventions_messages, print_stream=False
                )
                conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
                with open(conventions_file_path, "w") as f:
                    f.write(conventions_result)
                terminal_print(
                    f"\nProject conventions generated and saved to {conventions_file_path}",
                    PrintType.SUCCESS
                )
                return conventions_result
            except Exception as e:
                terminal_print(
                    f"Error generating project conventions: {str(e)}",
                    PrintType.ERROR
                )
                return None
        # --- End Nested Helper Functions ---

        # Create tasks
        conventions_task = asyncio.create_task(generate_conventions())
        file_analysis_tasks = [
            analyze_file(i, file_path)
            for i, file_path in enumerate(recommended_files)
        ]

        # Wait for all tasks
        results = await asyncio.gather(conventions_task, *file_analysis_tasks)

        conventions_result = results[0]
        file_analysis_results = results[1:]

        # Filter out None results from file analysis
        returned_analysis = [result for result in file_analysis_results if result]

        terminal_print(
            f"\nCompleted analysis of {len(returned_analysis)} recommended files.",
            PrintType.SUCCESS
        )

        # Print conventions result if available
        if conventions_result:
            terminal_print("\nProject Conventions Analysis:", PrintType.HEADER)
            terminal_print(conventions_result, PrintType.INFO) # Display generated conventions

        return returned_analysis, conventions_result

    except Exception as e:
        terminal_print(f"Error during analysis phase: {str(e)}", PrintType.ERROR)
        raise # Re-raise
    finally:
        terminal.model = original_model # Restore model after analysis phase


async def _generate_project_overview(
    terminal: Any,
    tree_file_path: str,
    context_file_path: str,
    conventions_result: Optional[str]
) -> None:
    """Generates the final project overview using all collected context."""
    original_model = terminal.model # Store model before overview
    try:
        terminal_print("\nGenerating project overview...", PrintType.PROCESSING)
        # Switch model for overview generation
        terminal.model = "deepseek-r1-671b"

        with open(tree_file_path, "r") as f:
            file_tree_content = f.read()
        with open(context_file_path, "r") as f:
            file_context_content = f.read()

        system_prompt = PromptManager.load("project_overview")
        overview_prompt = (
            f"FILE TREE:\n{file_tree_content}\n\n"
            f"FILE CONTEXT:\n{file_context_content}\n\n"
            f"PROJECT CONVENTIONS:\n{conventions_result or 'Not generated.'}" # Handle None case
        )

        overview_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": overview_prompt}
        ]
        full_overview = await stream_request(
            terminal, terminal.model, overview_messages
        )

        overview_file_path = f"{JRDEV_DIR}jrdev_overview.md"
        with open(overview_file_path, "w") as f:
            f.write(full_overview)

        terminal_print(
            f"\nProject overview generated and saved to {overview_file_path}",
            PrintType.SUCCESS
        )
    except Exception as e:
        terminal_print(
            f"Error generating project overview: {str(e)}",
            PrintType.ERROR
        )
        # Do not re-raise here, allow init to finish if possible
    finally:
        terminal.model = original_model # Restore model


async def handle_init(terminal: Any, args: List[str]) -> None:
    """
    Handle the /init command: generate file tree, get recommendations, analyze
    files and conventions, and create project overview.
    """
    start_time = time.time()
    terminal_print("Starting project initialization...", PrintType.INFO)
    original_model = terminal.model # Save initial model state

    tree_file_path = f"{JRDEV_DIR}jrdev_filetree.txt" # Default paths
    context_file_path = f"{JRDEV_DIR}jrdev_filecontext.md"

    try:
        # Step 1: Generate File Tree
        tree_file_path, tree_output, tree_files = await _generate_file_tree_and_paths(args)

        # Step 2: Get File Recommendations
        recommended_files = await _get_file_recommendations(terminal, tree_output)

        if not recommended_files:
            terminal_print("LLM did not recommend any files for analysis. Skipping analysis and overview.", PrintType.WARNING)
        else:
            # Step 3: Run Analysis and Conventions Generation
            _, conventions_result = await _run_analysis_and_conventions(
                terminal, recommended_files, tree_files, tree_output
            )

            # Step 4: Generate Project Overview
            await _generate_project_overview(
                terminal, tree_file_path, context_file_path, conventions_result
            )

        # Calculate and print elapsed time
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        terminal_print(
            f"\nProject initialization finished (took {int(minutes)}m {int(seconds)}s)",
            PrintType.SUCCESS
        )

    except Exception as e:
        # Catch errors from helper functions if they re-raised
        terminal_print(
            f"\nProject initialization failed due to an error: {str(e)}",
            PrintType.ERROR
        )
    finally:
        # Ensure the model is reset even if errors occur
        if terminal.model != original_model:
            terminal.model = original_model
            terminal_print(f"\nModel restored to: {terminal.model}", PrintType.INFO)