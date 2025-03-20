#!/usr/bin/env python3

"""
Init command implementation for the JrDev terminal.
"""
import asyncio
import os
import re

from jrdev.treechart import generate_tree, generate_compact_tree
from jrdev.llm_requests import stream_request
from jrdev.ui.ui import terminal_print, PrintType
from jrdev.file_utils import requested_files

# Create an asyncio lock for safe file access
context_file_lock = asyncio.Lock()


async def get_file_summary(terminal, file_path, context_file_path, additional_context=None):
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
                context_file.write(f"Error: File not found\n\n")
        return None

    # Read the file content
    try:
        with open(full_path, "r") as f:
            file_content = f.read()

        # Limit file size
        if len(file_content) > 1000*1024:
            terminal_print(f"File {full_path} is too large to send", PrintType.WARNING)
            return None

        # Create a prompt for the LLM
        text_prompt = """    
                            Role/Context: You are a code summarizer. Your goal is to produce a concise overview of the uploaded file.
                            Instructions:

                                Summarize the file's purpose and how it fits into the larger project.
                                Identify any important classes, functions, or data structures (or list key properties if it's a configuration file).
                                Emphasize the most relevant details for a quick understanding and omit low-value information.
                                Keep the summary brief—imagine that every token is precious.
                                If the file is a standard config (like package.json), focus primarily on the project dependencies, scripts, or other details that stand out, rather than describing the file's basic function.

                            Output Format:
                            Provide a short paragraph or a few bullet points that cover the essentials in a compact form. Do not include any conversational response, such as acknoledgement, or asking a question, as this is meant to be read by LLM's not humans.
                            """

        # Create a new chat thread for each file
        temp_messages = [{"role": "user", "content": file_content}, {"role": "system", "content": text_prompt}]
        if len(additional_context) > 0:
            temp_messages.append({"role": "assistant", "content": str(additional_context)})

        terminal_print(f"Waiting for LLM analysis of {file_path}...", PrintType.PROCESSING)
        
        # No need to print the file content when doing concurrent analysis
        
        # Send the request to the LLM
        file_analysis = await stream_request(terminal, terminal.model, temp_messages, print_stream=False)

        # Print the analysis
        terminal_print(f"\nFile Analysis for {file_path}:", PrintType.HEADER)
        terminal_print(file_analysis, PrintType.INFO)

        # Update the context file safely with a lock
        async with context_file_lock:
            with open(context_file_path, "a") as context_file:
                context_file.write(f"\n## {file_path}\n\n")
                context_file.write(f"{file_analysis}\n\n")

        terminal_print(f"\nFile analysis complete. Results saved to {context_file_path}", PrintType.SUCCESS)
        return f"Analysis for: {file_path} : {file_analysis}"

    except Exception as e:
        terminal_print(f"Error analyzing file {file_path}: {str(e)}", PrintType.ERROR)
        # Update the context file safely with a lock
        async with context_file_lock:
            with open(context_file_path, "a") as context_file:
                context_file.write(f"\n## {file_path}\n\n")
                context_file.write(f"Error: {str(e)}\n\n")
        return None

async def handle_init(terminal, args):
    """
    Handle the /init command to generate file tree, analyze files, and create project overview.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments
    """
    try:
        output_file = "jrdev_filetree.txt"
        if len(args) > 1:
            output_file = args[1]

        # Generate the tree structure using the token-efficient format
        current_dir = os.getcwd()
        tree_output = generate_compact_tree(current_dir, output_file)

        terminal_print(f"File tree generated and saved to {output_file}", PrintType.SUCCESS)

        # Switch the model to deepseek-r1-671b
        previous_model = terminal.model
        terminal.model = "deepseek-r1-671b"
        terminal_print(f"Model changed to: {terminal.model}", PrintType.INFO)

        # Send the file tree to the LLM with a request for file recommendations
        terminal_print("Waiting for LLM analysis of project tree...", PrintType.PROCESSING)

        # Send the file tree to the LLM with the recommendation request
        dev_prompt = (
            f"Respond only with a list of files in the format get_files ['path/to/file.cpp', 'path/to/file2.json', ...] etc. "
            f"Do not include any other text or communication.\n\n"
        )
        
        # Create a description of the compact format if using compact tree
        format_explanation = (
            f"The project structure below is in a compact format for efficiency:\n"
            f"- ROOT=directory_name: The root directory name\n"
            f"- path/to/dir:[file1,file2,...]: Files in a directory\n"
            f"Each line represents either the root directory or a directory with its files.\n\n"
        )
        
        recommendation_prompt = (
            f"Given this project structure, what files would you select to find out the "
            f"most important context about the project, choose up to 20 files?\n\n"
            f"{format_explanation}{tree_output}"
        )

        # Create a temporary message list to avoid polluting the main conversation history
        temp_messages = [{"role": "user", "content": recommendation_prompt}, {"role": "system", "content": dev_prompt}]

        # Send the request to the LLM
        try:
            recommendation_response = await stream_request(terminal, terminal.model, temp_messages)

            # Print the LLM's response
            terminal_print("\nLLM File Recommendations:", PrintType.HEADER)
            terminal_print(recommendation_response, PrintType.INFO)

            # Parse the file list from the response
            try:
                recommended_files = requested_files(recommendation_response)
                terminal_print(f"requesting {len(recommended_files)} files", PrintType.PROCESSING)

                # Now switch to a different model for file analysis
                terminal.model = "qwen-2.5-qwq-32b"
                terminal_print(f"\nSwitching model to: {terminal.model} for file analysis", PrintType.INFO)

                # Initialize the context file
                context_file_path = "jrdev_filecontext.md"
                with open(context_file_path, "w") as context_file:
                    context_file.write(f"# Project Context Analysis\n\n")
                    context_file.write(
                        f"Files analyzed: {len(recommended_files)}\n\n"
                    )

                # Process all recommended files concurrently
                terminal_print(f"\nAnalyzing {len(recommended_files)} files concurrently...", PrintType.PROCESSING)

                async def analyze_file(index, file_path):
                    terminal_print(f"Starting analysis for file {index + 1}/{len(recommended_files)}: {file_path}", PrintType.PROCESSING)
                    result = await get_file_summary(terminal, file_path, context_file_path)
                    terminal_print(f"Completed analysis for file {index + 1}/{len(recommended_files)}: {file_path}", PrintType.SUCCESS)
                    return result
                
                # Create tasks for all files
                tasks = [analyze_file(i, file_path) for i, file_path in enumerate(recommended_files)]
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # Filter out None results
                returned_analysis = [result for result in results if result]
                
                terminal_print(f"\nCompleted analysis of all {len(returned_analysis)} files", PrintType.SUCCESS)

                # Now create a project overview with deepseek-r1-671b
                terminal_print("\nGenerating project overview...", PrintType.PROCESSING)
                terminal.model = "deepseek-r1-671b"

                # Read the file tree and context file
                with open(output_file, "r") as f:
                    file_tree_content = f.read()

                with open(context_file_path, "r") as f:
                    file_context_content = f.read()

                # Create the overview prompt
                system_prompt = (
                    f"Given the file tree and the uploaded file context's, give a 2 paragraph descriptive "
                    f"overview of the project. Only respond with the 2 paragraphs and no other questions "
                    f"or conversation. The response will be read by both LLM's and humans, so write it accordingly. "
                    f"format response as markdown\n\n"
                )
                overview_prompt = (
                    f"FILE TREE:\n{file_tree_content}\n\n"
                    f"FILE CONTEXT:\n{file_context_content}"
                )

                # Send request to the model
                try:
                    overview_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": overview_prompt}
                    ]
                    full_overview = await stream_request(terminal, terminal.model, overview_messages)

                    # Save to markdown file
                    overview_file_path = "jrdev_overview.md"
                    with open(overview_file_path, "w") as f:
                        f.write(full_overview)

                    terminal_print(f"\nProject overview generated and saved to {overview_file_path}", PrintType.SUCCESS)
                except Exception as e:
                    terminal_print(f"Error generating project overview: {str(e)}", PrintType.ERROR)

                terminal_print("\nProject initialization finished", PrintType.SUCCESS)
            except Exception as e:
                terminal_print(f"Error processing file recommendations: {str(e)}", PrintType.ERROR)
        except Exception as e:
            terminal_print(f"Error getting LLM recommendations: {str(e)}", PrintType.ERROR)
    except Exception as e:
        terminal_print(f"Error generating file tree: {str(e)}", PrintType.ERROR)
