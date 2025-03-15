#!/usr/bin/env python3

"""
Code command implementation for the JrDev terminal.
Sends message with code processing enabled.
"""

import asyncio
import os
import logging
from typing import Any, Dict, List

from jrdev.ui import terminal_print, PrintType
from jrdev.llm_requests import stream_request
from jrdev.file_utils import requested_files, get_file_contents, check_and_apply_code_changes


async def handle_code(terminal: Any, args: List[str]) -> None:
    """
    Handle the /code command which sends a message with code processing enabled.

    This is a convenience wrapper around send_simple_message with process_follow_up=True
    to automatically handle file requests and code changes.

    Args:
        terminal: The JrDevTerminal instance
        args: Command arguments (message content)
    """
    if len(args) < 2:
        terminal_print("Usage: /code <message>", print_type=PrintType.ERROR)
        return

    # Combine all arguments after the command into a single message
    message = " ".join(args[1:])

    # Send the message with code processing enabled
    await send_code_request(terminal, message)


async def send_code_request(terminal: Any, user_task: str):
    """
    Send a message to the LLM without processing follow-up tasks like file requests
    and code changes unless explicitly requested.

    Args:
        terminal: The JrDevTerminal instance
        user_task: The message content to send
        process_follow_up: Whether to process follow-up tasks like file requests and code changes
    
    Returns:
        str: The response text from the model
    """
    terminal.logger.info(f"Sending message to model {terminal.model}")
    
    if not isinstance(user_task, str):
        error_msg = f"Expected string but got {type(user_task)}"
        terminal.logger.error(error_msg)
        terminal_print(f"Error: {error_msg}", PrintType.ERROR)
        return
        
    # Read project context files if they exist
    project_context = {}
    for key, filename in terminal.project_files.items():
        try:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    project_context[key] = f.read()
        except Exception as e:
            warning_msg = f"Could not read {filename}: {str(e)}"
            terminal.logger.warning(warning_msg)
            terminal_print(f"Warning: {warning_msg}", PrintType.WARNING)

    # Build the complete message
    dev_prompt_modifier = (
        "You are an expert software architect and engineer reviewing an attached project. An engineer from the project is asking for guidance on how to complete a specific task. Begin by providing a high-level analysis of the task, outlining the necessary steps and strategy without including any code changes. "
        "**CRITICAL:** Do not propose any code modifications until you have received and reviewed the full content of the relevant file(s). If the file content is not yet in your context, request it using the exact format: "
        "'get_files [\"path/to/file1.txt\", \"path/to/file2.cpp\", ...]'. Only after the complete file content is available should you suggest code changes."
    )

    user_additional_modifier = " Here is the task to complete:"
    user_message = f"{user_additional_modifier} {user_task}"

    if terminal.model not in terminal.messages:
        terminal.messages[terminal.model] = []

    # Append project context if available (only needed on first run)
    if project_context:
        for key, value in project_context.items():
            user_message = f"{user_message}\n\n{key.upper()}:\n{value}"
    if dev_prompt_modifier is not None:
        terminal.messages[terminal.model].append({"role": "system", "content": dev_prompt_modifier})
    
    # Add any additional context files stored in terminal.context
    if terminal.context:
        context_section = "\n\nUSER CONTEXT:\n"
        for i, ctx in enumerate(terminal.context):
            context_section += f"\n--- Context File {i+1}: {ctx['name']} ---\n{ctx['content']}\n"
        user_message += context_section

    terminal.messages[terminal.model].append({"role": "user", "content": user_message})

    model_name = terminal.model
    terminal_print(f"\n{model_name} is processing request...", PrintType.PROCESSING)

    try:
        response_text = await stream_request(terminal.client, terminal.model, terminal.messages[terminal.model])
        # Add a new line after streaming completes
        terminal_print("", PrintType.INFO)
        
        # Always add response to messages
        terminal.messages[terminal.model].append({"role": "assistant", "content": response_text})

        await process_code_request_response(terminal, response_text, user_task)
    except Exception as e:
        error_msg = str(e)
        terminal.logger.error(f"Error in send_code_request: {error_msg}")
        terminal_print(f"Error: {error_msg}", PrintType.ERROR)


async def double_check_changed_files(terminal, filelist):
    """
    Sends the changed files to the LLM for validation to check if they are malformed.
    
    Args:
        terminal: The JrDevTerminal instance
        filelist: List of files that were changed
        
    Returns:
        bool: True if files are valid, False if malformed
    """
    if not filelist:
        terminal.logger.info("No files were changed, skipping validation")
        return True
    
    terminal.logger.info(f"Validating {len(filelist)} changed files: {filelist}")
    terminal_print(f"\nValidating changed files...", PrintType.PROCESSING)
    
    # Get the content of all changed files
    files_content = get_file_contents(filelist)
    
    validation_prompt = (
        "You are a code validator. Review the following file(s) that were just modified "
        "and check if they are properly formatted and not malformed. "
        "ONLY respond with 'VALID' if all files look correct, or 'INVALID: [reason]' if any file appears malformed. "
        "Be strict about syntax errors, indentation problems, unclosed brackets/parentheses, "
        "and other issues that would cause runtime errors. "
        "Keep your response to a single line."
    )
    
    # Create a temporary messages array for this request only
    validation_messages = [
        {"role": "system", "content": validation_prompt},
        {"role": "user", "content": f"Please validate these files:{files_content}"}
    ]
    
    try:
        # Don't print the stream for this validation check (print_stream=False)
        validation_response = await stream_request(
            terminal.client, 
            terminal.model, 
            validation_messages,
            print_stream=False
        )
        
        terminal.logger.info(f"Validation response: {validation_response}")
        
        # Check if the validation response indicates the files are valid
        if validation_response.strip().startswith("VALID"):
            terminal_print("✓ Files validated successfully", PrintType.SUCCESS)
            return True
        elif "INVALID" in validation_response:
            # Extract the reason from the response
            reason = validation_response.split("INVALID:")[1].strip() if ":" in validation_response else "Unspecified error"
            terminal_print(f"⚠ Files may be malformed: {reason}", PrintType.ERROR)
            return False
        else:
            # If the response doesn't match our expected format
            terminal_print("⚠ Could not determine if files are valid", PrintType.WARNING)
            terminal.logger.warning(f"Unexpected validation response: {validation_response}")
            return True  # Default to true to not block the process
    except Exception as e:
        terminal.logger.error(f"Error in double_check_changed_files: {str(e)}")
        terminal_print(f"Error validating files: {str(e)}", PrintType.ERROR)
        return True  # Default to true to not block the process


async def process_code_request_response(terminal, response_prev, user_task):
    # Process file requests if present
    files_to_send = requested_files(response_prev)

    terminal.logger.info(f"Found file request, sending files: {files_to_send}")
    response = await send_file_request(terminal, files_to_send, user_task, response_prev)

    # Process code changes in the response
    terminal.logger.info(f"Processing code changes from response\n RESPONSE:\n {response}")
    files_changed = check_and_apply_code_changes(response)

    if files_changed:
        # Validate the changed files to ensure they're not malformed
        model_prev = terminal.model
        terminal.model = "qwen-2.5-coder-32b"
        is_valid = await double_check_changed_files(terminal, files_changed)
        terminal.model = model_prev

        if not is_valid:
            terminal_print(
                "\nDetected possible issues in the changed files. Please review them manually.",
                PrintType.WARNING
            )
            # Here you could add more sophisticated error handling or recovery
            # For now, we just warn the user but don't try to fix automatically
    else:
        terminal.logger.info("No files were changed during this request")


async def send_file_request(terminal, files_to_send, user_task, assistant_plan):
    terminal.logger.info(f"Detected file request: {files_to_send}")
    terminal_print(f"\nDetected file request: {files_to_send}", PrintType.INFO)

    files_content = get_file_contents(files_to_send)

    dev_msg = (
        """
        You are an expert software engineer and code reviewer. Instead of rewriting the entire file, provide only the necessary modifications as a diff. 
        Format your response as a JSON object with a "changes" key that contains an array of changes. You have three ways to specify changes:

        1. DELETE: Existing code using line numbers to delete code:
        - "filename": the name of the file to modify
        - "operation": "DELETE"
        - "start_line": the starting line number
        - "end_line": the ending line number (inclusive)

        2. ADD: Add new code, using content reference to specify positioning:
        - "filename": the name of the file to modify
        - "insert_after_line": a unique line of existing code after which to insert
        - "new_content": the code to insert after the specified line
        - "sub_type": specifies the type of addition:
            - "FUNCTION": a new function implementation, including the full scope of the function.
            - "BLOCK": lines of code added within an existing function or structure

        3. Creating a new file:
        - "operation": "NEW"
        - "filename": the path of the new file to create
        - "new_content": the entire content of the new file

        When using the "insert_after_line" approach, make sure to choose a distinctive line that appears exactly once in the file.

        Wrap your response in ```json and ``` markers. Use \\n for line breaks in new_content.
        Do not include any additional commentary or explanation outside the JSON.
        """
    )

    #construct and send message to LLM
    messages = []
    messages.append({"role": "system", "content": dev_msg})
    messages.append({"role": "assistant", "content": assistant_plan})
    messages.append({"role": "user", "content": f"Task To Accomplish: {user_task}"})
    messages.append({"role": "user", "content": files_content})
    terminal.logger.info(f"Sending requested files to {terminal.model}")
    terminal_print(f"\nSending requested files to {terminal.model}...", PrintType.PROCESSING)

    follow_up_response = await stream_request(terminal.client, terminal.model, messages)
    terminal_print("", PrintType.INFO)
    terminal.messages[terminal.model].append({"role": "assistant", "content": follow_up_response})

    return follow_up_response
