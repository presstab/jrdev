#!/usr/bin/env python3

"""
Init command implementation for the JrDev terminal.
"""
import asyncio
import os
import time
from typing import List, Optional, Any, Dict


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
            return None

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

        # No need to print the file content when doing concurrent analysis

        # Send the request to the LLM
        file_analysis = await stream_request(
            terminal, terminal.model, temp_messages, print_stream=False
        )

        # Print the analysis
        terminal_print(f"\nFile Analysis for {file_path}:", PrintType.HEADER)
        terminal_print(file_analysis, PrintType.INFO)

        # Update the context file safely with a lock
        async with context_file_lock:
            with open(context_file_path, "a") as context_file:
                context_file.write(f"\n## {file_path}\n\n")
                context_file.write(f"{file_analysis}\n\n")

        terminal_print(
            f"\nFile analysis complete. Results saved to {context_file_path}",
            PrintType.SUCCESS
        )
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
                context_file.write(f"Error: {str(e)}\n\n")
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
            f"File tree generated and saved to {output_file}",
            PrintType.SUCCESS
        )

        # Switch the model to deepseek-r1-671b
        terminal.model = "deepseek-r1-671b"
        terminal_print(f"Model changed to: {terminal.model}", PrintType.INFO)

        # Send the file tree to the LLM with a request for file recommendations
        terminal_print(
            "Waiting for LLM analysis of project tree...",
            PrintType.PROCESSING
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
            {"role": "user", "content": recommendation_prompt}
        ]

        # Send the request to the LLM
        try:
            recommendation_response = await stream_request(
                terminal, terminal.model, temp_messages
            )

            # Print the LLM's response
            terminal_print("\nLLM File Recommendations:", PrintType.HEADER)
            terminal_print(recommendation_response, PrintType.INFO)

            # Parse the file list from the response
            try:
                recommended_files = requested_files(recommendation_response)
                terminal_print(
                    f"requesting {len(recommended_files)} files",
                    PrintType.PROCESSING
                )

                # Now switch to a different model for file analysis
                terminal.model = "qwen-2.5-qwq-32b"
                terminal_print(
                    f"\nSwitching model to: {terminal.model} for analysis",
                    PrintType.INFO
                )

                # Initialize the context file
                context_file_path = f"{JRDEV_DIR}jrdev_filecontext.md"
                with open(context_file_path, "w") as context_file:
                    context_file.write("# Project Context Analysis\n\n")
                    context_file.write(
                        f"Files analyzed: {len(recommended_files)}\n\n"
                    )

                # Process all recommended files concurrently
                terminal_print(
                    f"\nAnalyzing {len(recommended_files)} files concurrently...",
                    PrintType.PROCESSING
                )

                async def analyze_file(index: int, file_path: str) -> Optional[str]:
                    """Helper function to analyze a single file."""
                    terminal_print(
                        f"Starting analysis for file {index + 1}/"
                        f"{len(recommended_files)}: {file_path}",
                        PrintType.PROCESSING
                    )
                    result = await get_file_summary(
                        terminal, file_path, context_file_path
                    )
                    terminal_print(
                        f"Completed analysis for file {index + 1}/"
                        f"{len(recommended_files)}: {file_path}",
                        PrintType.SUCCESS
                    )
                    return result

                # Start file analysis tasks
                file_analysis_tasks = [
                    analyze_file(i, file_path)
                    for i, file_path in enumerate(recommended_files)
                ]

                # Parallel task to generate conventions using the same files
                async def generate_conventions() -> None:
                    """Generate project conventions in parallel with file analysis."""
                    # First wait a short time to let some file analysis start
                    await asyncio.sleep(0.5)
                    
                    terminal_print(
                        f"\Analyzing project conventions...",
                        PrintType.PROCESSING
                    )
                    
                    # Save current model to restore it later
                    current_model = terminal.model
                    
                    # Get project conventions prompt
                    conventions_prompt = PromptManager.load("project_conventions")
                    
                    # We'll wait for the context file to have some content before proceeding
                    while True:
                        if os.path.exists(context_file_path):
                            file_size = os.path.getsize(context_file_path)
                            if file_size > 100:  # Ensure we have some meaningful content
                                break
                        await asyncio.sleep(0.5)  # Check every half second
                    
                    # Read the file tree and initial context file
                    with open(output_file, "r") as f:
                        file_tree_content = f.read()
                    
                    with open(context_file_path, "r") as f:
                        file_context_content = f.read()
                    
                    # Create conventions messages with all the files being analyzed
                    conventions_messages = [
                        {"role": "system", "content": conventions_prompt},
                        {"role": "user", "content": f"FILE TREE:\n{file_tree_content}\n\nFILE CONTEXT:\n{file_context_content}"}
                    ]
                    
                    try:
                        # Temporarily switch to Qwen model for conventions analysis
                        terminal.model = "mistral-31-24b"
                        
                        # Send request to generate conventions but don't stream
                        conventions_result = await stream_request(
                            terminal, terminal.model, conventions_messages, print_stream=False
                        )
                        
                        # Save to markdown file
                        conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
                        with open(conventions_file_path, "w") as f:
                            f.write(conventions_result)
                        
                        # Don't print results here - we'll print them after all file analyses are complete
                    except Exception as e:
                        terminal_print(
                            f"Error generating project conventions: {str(e)}",
                            PrintType.ERROR
                        )
                    finally:
                        # Restore the original model
                        terminal.model = current_model

                # Create a task for generating conventions in parallel
                conventions_task = asyncio.create_task(generate_conventions())
                
                # Wait for all file analysis tasks to complete
                results = await asyncio.gather(*file_analysis_tasks)

                # Filter out None results
                returned_analysis = [result for result in results if result]

                terminal_print(
                    f"\nCompleted analysis of all {len(returned_analysis)} files",
                    PrintType.SUCCESS
                )

                # Check if conventions are done, but don't wait
                conventions_ready = conventions_task.done()
                conventions_file_path = f"{JRDEV_DIR}jrdev_conventions.md"
                
                # If conventions are ready, print them before overview
                if conventions_ready and os.path.exists(conventions_file_path):
                    try:
                        with open(conventions_file_path, "r") as f:
                            conventions_result = f.read()
                            
                        terminal_print("\nProject Conventions Analysis:", PrintType.HEADER)
                        terminal_print(conventions_result, PrintType.INFO)
                        
                        terminal_print(
                            f"\nProject conventions generated and saved to "
                            f"{conventions_file_path}",
                            PrintType.SUCCESS
                        )
                    except Exception as e:
                        terminal_print(
                            f"Error reading conventions file: {str(e)}",
                            PrintType.ERROR
                        )

                # Start project overview immediately regardless of conventions status
                terminal_print("\nGenerating project overview...",
                               PrintType.PROCESSING)
                terminal.model = "deepseek-r1-671b"

                # Read the file tree and context file
                with open(output_file, "r") as f:
                    file_tree_content = f.read()

                with open(context_file_path, "r") as f:
                    file_context_content = f.read()

                # Get project overview prompt
                system_prompt = PromptManager.load("project_overview")

                # Create the overview prompt
                overview_prompt = (
                    f"FILE TREE:\n{file_tree_content}\n\n"
                    f"FILE CONTEXT:\n{file_context_content}"
                )

                # Send request to the model for project overview
                try:
                    overview_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": overview_prompt}
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
                        PrintType.SUCCESS
                    )
                except Exception as e:
                    terminal_print(
                        f"Error generating project overview: {str(e)}",
                        PrintType.ERROR
                    )
                
                # Now check if conventions need to be printed after overview
                if not conventions_ready:
                    try:
                        # Wait for conventions to complete if not done yet
                        if not conventions_task.done():
                            terminal_print(
                                "\nWaiting for project conventions analysis to complete...",
                                PrintType.PROCESSING
                            )
                            await conventions_task
                        
                        # Print conventions if the file exists
                        if os.path.exists(conventions_file_path):
                            with open(conventions_file_path, "r") as f:
                                conventions_result = f.read()
                                
                            terminal_print("\nProject Conventions Analysis:", PrintType.HEADER)
                            terminal_print(conventions_result, PrintType.INFO)
                            
                            terminal_print(
                                f"\nProject conventions generated and saved to "
                                f"{conventions_file_path}",
                                PrintType.SUCCESS
                            )
                    except Exception as e:
                        terminal_print(
                            f"Error handling conventions after overview: {str(e)}",
                            PrintType.ERROR
                        )
                
                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                minutes, seconds = divmod(elapsed_time, 60)
                
                terminal_print(
                    f"\nProject initialization finished (took {int(minutes)}m {int(seconds)}s)",
                    PrintType.SUCCESS
                )
            except Exception as e:
                terminal_print(
                    f"Error processing file recommendations: {str(e)}",
                    PrintType.ERROR
                )
        except Exception as e:
            terminal_print(
                f"Error getting LLM recommendations: {str(e)}",
                PrintType.ERROR
            )
    except Exception as e:
        terminal_print(
            f"Error generating file tree: {str(e)}",
            PrintType.ERROR
        )