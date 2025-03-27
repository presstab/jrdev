#!/usr/bin/env python3

"""
Code command implementation for the JrDev terminal.
Sends message with code processing enabled.
"""

import os
from typing import Any, List

from jrdev.file_operations.process_ops import apply_file_changes
from jrdev.file_utils import requested_files, get_file_contents, cutoff_string, manual_json_parse
from jrdev.llm_requests import stream_request
from jrdev.prompts.prompt_utils import PromptManager
from jrdev.ui.ui import terminal_print, PrintType, print_steps


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

    # Send the message, cache message history, and replace after
    current_messages = terminal.message_history()
    try:
        await send_code_request(terminal, message)
    finally:
        # Clear model's messages accrued from this code session
        terminal.set_message_history(current_messages)

    # todo good entry point for devlog history here


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

    # Load prompt using PromptManager
    dev_prompt_modifier = PromptManager.load("analyze_task_return_getfiles")

    user_additional_modifier = " Here is the task to complete:"
    user_message = f"{user_additional_modifier} {user_task}"

    # Append project context if available (only needed on first run)
    if project_context:
        for key, value in project_context.items():
            user_message = f"{user_message}\n\n{key.upper()}:\n{value}"

    # start message thread with no history
    messages = []
    if dev_prompt_modifier is not None:
        messages.append({"role": "system", "content": dev_prompt_modifier})

    # Add any additional context files stored in terminal.context
    if terminal.context:
        context_section = "\n\nUSER CONTEXT:\n"
        for i, ctx in enumerate(terminal.context):
            context_section += f"\n--- Context File {i+1}: {ctx['name']} ---\n{ctx['content']}\n"
        user_message += context_section

    messages.append({"role": "user", "content": user_message})

    model_name = terminal.model
    terminal_print(f"\n{model_name} is processing request...", PrintType.PROCESSING)

    try:
        response_text = await stream_request(terminal, terminal.model, messages)
        # Add a new line after streaming completes
        terminal_print("", PrintType.INFO)

        # Always add response to messages
        messages.append({"role": "assistant", "content": response_text})

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

    # Load validation prompt
    validation_prompt = PromptManager.load("validator")

    # Create a temporary messages array for this request only
    validation_messages = [
        {"role": "system", "content": validation_prompt},
        {"role": "user", "content": f"Please validate these files:{files_content}"}
    ]

    try:
        # Don't print the stream for this validation check (print_stream=False)
        validation_response = await stream_request(
            terminal,
            terminal.model,
            validation_messages,
            print_stream=False
        )

        terminal.logger.info(f"Validation response: {validation_response}")

        # Check if the validation response indicates the files are valid
        if validation_response.strip().startswith("VALID"):
            terminal_print("✓ Files validated successfully", PrintType.SUCCESS)
            return None
        elif "INVALID" in validation_response:
            # Extract the reason from the response
            reason = validation_response.split("INVALID:")[1].strip() if ":" in validation_response else "Unspecified error"
            terminal_print(f"⚠ Files may be malformed: {reason}", PrintType.ERROR)
            return reason
        else:
            # If the response doesn't match our expected format
            terminal_print("⚠ Could not determine if files are valid", PrintType.WARNING)
            terminal.logger.warning(f"Unexpected validation response: {validation_response}")
            return None  # Default to true to not block the process
    except Exception as e:
        terminal.logger.error(f"Error in double_check_changed_files: {str(e)}")
        terminal_print(f"Error validating files: {str(e)}", PrintType.ERROR)
        return None


async def complete_step(terminal, step, files_to_send, retry_message=None):
    terminal.logger.info(f"step: {step}")
    filepath = step["filename"]
    terminal.logger.info("filecheck")
    # file_check = [f for f in files_to_send if f == filepath]
    # if file_check is None:
    #     raise Exception(f"process_code_request unable to find file {filepath}")

    terminal.logger.info("file_content")
    file_content = f"{get_file_contents(files_to_send)}"
    # send request for LLM to complete changes in step
    code_change_response = await request_code(terminal, step, file_content, retry_message)

    # todo some kind of sanity check here? or just one sanity check at the very end?

    # Process code changes in the response
    terminal.logger.info(f"Processing code changes from response\n RESPONSE:\n {code_change_response}")

    try:
        result = check_and_apply_code_changes(code_change_response)
        if result["success"]:
            return result["files_changed"]

        if "change_requested" in result:
            retry_message = result["change_requested"]
            terminal_print("retry step with user feedback")
            return await complete_step(terminal, step, files_to_send, retry_message)

        raise Exception("Failed to apply any code changes")

    except Exception:
        # file change failed, try again
        terminal_print("failed step, try again later.", PrintType.ERROR)
        return []


def check_and_apply_code_changes(response_text):
    changes = None
    try:
        cutoff = cutoff_string(response_text, "```json", "```")
        changes = manual_json_parse(cutoff)
    except Exception as e:
        raise Exception(f"parsing failed in check_and_apply_code_changes: {str(e)}")
    if "changes" in changes:
        return apply_file_changes(changes)

    return {"success": False}



async def process_code_request_response(terminal, response_prev, user_task):
    # Process file requests if present
    files_to_send = requested_files(response_prev)

    # send file requests, get a list of steps
    terminal.logger.info(f"Found file request, sending files: {files_to_send}")
    response = await send_file_request(terminal, files_to_send, user_task, response_prev)

    # parse steps response
    steps = await parse_steps(response, files_to_send)
    if "steps" not in steps or len(steps["steps"]) == 0:
        raise Exception("failed to process steps")

    terminal.logger.info(f"parsed_steps successfully: steps:\n {steps}")
    
    # Print initial steps in to do list format
    print_steps(terminal, steps)

    # Track completed steps (0-based indices)
    completed_steps = []
    
    # turn each step into individual code changes
    files_changed_set = set()
    failed_steps = []
    
    # First pass through all steps
    for i, step in enumerate(steps["steps"]):
        # Show current step being worked on
        print_steps(terminal, steps, completed_steps, current_step=i)
        
        # Execute the step
        terminal_print(f"Working on step {i+1}: {step.get('operation_type')} for {step.get('filename')}", PrintType.PROCESSING)
        new_file_changes = await complete_step(terminal=terminal, step=step, files_to_send=files_to_send)
        
        if len(new_file_changes) > 0:
            # Mark step as completed
            completed_steps.append(i)
            # Update the TODO list to show progress
            print_steps(terminal, steps, completed_steps)
            
            # Track changed files
            for f in new_file_changes:
                files_changed_set.add(f)
        else:
            failed_steps.append((i, step))

    # Second pass for failed steps
    for step_idx, step in failed_steps:
        terminal_print(f"Retrying step {step_idx + 1}", PrintType.PROCESSING)
        
        # Show current step being retried
        print_steps(terminal, steps, completed_steps, current_step=step_idx)
        
        new_file_changes = await complete_step(terminal=terminal, step=step, files_to_send=files_to_send)

        if len(new_file_changes) > 0:
            # Mark step as completed
            completed_steps.append(step_idx)
            # Update the TODO list to show progress
            print_steps(terminal, steps, completed_steps)
            
            # Track changed files
            for f in new_file_changes:
                files_changed_set.add(f)

    if len(files_changed_set):
        terminal.logger.info("send files for sanity check")
        # Validate the changed files to ensure they're not malformed
        model_prev = terminal.model
        terminal.model = "qwen-2.5-coder-32b"
        error_msg = await double_check_changed_files(terminal, files_changed_set)
        # if error_msg is not None:
        #     files_changed = await send_file_request(terminal, files_changed, error_msg)
        #     error_msg = await double_check_changed_files(terminal, files_changed)

        terminal.model = model_prev

        if error_msg is not None:
            terminal_print(
                "\nDetected possible issues in the changed files. Please review them manually.",
                PrintType.WARNING
            )
            # Here you could add more sophisticated error handling or recovery
            # For now, we just warn the user but don't try to fix automatically
    else:
        terminal.logger.info("No files were changed during this request")



async def parse_steps(steps_text, filelist):
    """
    Parse steps from a text file that contains instructions for code changes,
    and verify that all referenced files exist in the provided filelist.

    Args:
        steps_text (str): The content of the steps text file.
        filelist (list): List of files that are available.

    Returns:
        dict: A dictionary containing the parsed steps.
    """
    from jrdev.file_utils import cutoff_string, manual_json_parse
    import logging
    import os

    logger = logging.getLogger("jrdev")

    # Extract the JSON content using cutoff_string
    json_content = cutoff_string(steps_text, "```json", "```")

    # Parse the JSON content
    steps_json = manual_json_parse(json_content)

    if "steps" not in steps_json:
        logger.warning("No steps found in the steps file")
        return {"steps": []}

    # Check if each filename referenced in steps exists in filelist
    missing_files = []
    for step in steps_json["steps"]:
        if "filename" in step:
            filename = step["filename"]
            # Convert filelist paths to basenames for comparison
            basename = os.path.basename(filename)
            found = False

            for file_path in filelist:
                if os.path.basename(file_path) == basename or file_path == filename:
                    found = True
                    break

            if not found:
                missing_files.append(filename)

    if missing_files:
        logger.warning(f"Files not found in filelist: {missing_files}")
        # Add a warning to the steps_json
        steps_json["missing_files"] = missing_files

    return steps_json


def get_operation_prompt(op_type):
    """Load operation prompt from markdown file"""
    return PromptManager.load(f"operations/{op_type.lower()}")


async def request_code(terminal, change_instruction, file, additional_prompt=None):
    op_type = change_instruction["operation_type"]
    operation_prompt = get_operation_prompt(op_type)
    
    # Load implement_step prompt template and replace {operation_prompt} placeholder
    dev_msg_template = PromptManager.load("implement_step")
    dev_msg = dev_msg_template.replace("{operation_prompt}", operation_prompt)

    prompt = (
        f"""
        You have been tasked with using the {op_type} operation to {change_instruction["description"]}. This should be 
        applied to the supplied file {change_instruction["filename"]} and you will need to locate the proper location in 
        the code to apply this change. The target location is {change_instruction["target_location"]}. Operations should 
        only be applied to this location, or else the task will fail.
        """
    )
    if additional_prompt is not None:
        prompt = f"{prompt} {additional_prompt}"

    # construct and send message to LLM
    messages = []
    messages.append({"role": "system", "content": dev_msg})
    messages.append({"role": "user", "content": file})
    messages.append({"role": "user", "content": prompt})
    terminal.logger.info(f"Sending code request to {terminal.model}")
    terminal_print(f"\nSending code request to {terminal.model}...", PrintType.PROCESSING)

    follow_up_response = await stream_request(terminal, terminal.model, messages)
    terminal_print("", PrintType.INFO)
    terminal.add_message_history(follow_up_response, is_assistant=True)

    return follow_up_response


async def send_file_request(terminal, files_to_send, user_task, assistant_plan = None):
    terminal.logger.info(f"Detected file request: {files_to_send}")
    terminal_print(f"\nDetected file request: {files_to_send}", PrintType.INFO)

    files_content = get_file_contents(files_to_send)

    # Load create_steps prompt
    dev_msg = PromptManager.load("create_steps")

    #construct and send message to LLM
    messages = []
    messages.append({"role": "system", "content": dev_msg})
    if assistant_plan is not None:
        messages.append({"role": "assistant", "content": assistant_plan})
    messages.append({"role": "user", "content": f"Task To Accomplish: {user_task}"})
    messages.append({"role": "user", "content": files_content})
    terminal.logger.info(f"Sending requested files to {terminal.model}")
    terminal_print(f"\nSending requested files to {terminal.model}...", PrintType.PROCESSING)

    follow_up_response = await stream_request(terminal, terminal.model, messages)
    terminal_print("", PrintType.INFO)

    return follow_up_response
