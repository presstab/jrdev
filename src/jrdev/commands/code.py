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
        "'get_files [\"path/to/file1.txt\", \"path/to/file2.cpp\", ...]'. This is your one chance to request files, so be sure to get all files that will be "
        "needed to successfully complete the task. "
        "Only after the complete file content is available should you suggest code changes."
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
        response_text = await stream_request(terminal, terminal.model, terminal.messages[terminal.model])
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
        "ONLY respond with 'VALID' if all files look correct, or 'INVALID: [filename][reason], [file2name][reason2]' if any file appears malformed. "
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


async def complete_step(terminal, step, files_to_send):
    terminal.logger.info(f"step: {step}")
    filepath = step["filename"]
    terminal.logger.info("filecheck")
    file_check = [f for f in files_to_send if f == filepath]
    if file_check is None:
        raise Exception(f"process_code_request unable to find file {filepath}")

    terminal.logger.info("file_content")
    file_content = get_file_contents([filepath])
    # send request for LLM to complete changes in step
    code_change_response = await request_code(terminal, step, file_content)

    # todo some kind of sanity check here? or just one sanity check at the very end?

    # Process code changes in the response
    terminal.logger.info(f"Processing code changes from response\n RESPONSE:\n {code_change_response}")

    try:
        return check_and_apply_code_changes(code_change_response)
    except Exception:
        # file change failed, try again
        terminal_print("failed step, try again later.", PrintType.ERROR)
        return []


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

    # turn each step into individual code changes
    files_changed_set = set()
    failed_steps = []
    for step in steps["steps"]:
        new_file_changes = await complete_step(terminal=terminal, step=step, files_to_send=files_to_send)
        if len(new_file_changes) == 0:
            failed_steps.append(step)

        # only track each file once
        for f in new_file_changes:
            files_changed_set.add(f)

    # try any failed steps again
    for step in failed_steps:
        terminal_print(f"Retrying step {step}", PrintType.PROCESSING)
        new_file_changes = await complete_step(terminal=terminal, step=step, files_to_send=files_to_send)

        # only track each file once
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


operation_promts = {
    "DELETE": (
        """
        DELETE: Remove existing code using code references rather than line numbers.
           - "operation": "DELETE"
           - "filename": the file to modify.
           - "target": an object specifying what to delete. It may include:
               - "function": the name of a function to delete.
               - "block": a block within a function, identified by the function name and a "position_marker" (e.g., "before_return", "after_variable_declaration").
        """
    ),
    "ADD": (
        """
        ADD: Insert new code at a specified location using code references. This operation will insert as a new line, be mindful of needed indentations.
           - "operation": "ADD"
           - "filename": the file to modify.
           - "insert_location": an object that indicates where to insert the new code. Options include:
               - "after_function": the name of a function after which to insert.
               - "within_function": the name of a function, along with a "position_marker" to pinpoint the insertion spot (e.g., "at_start", "before_return").
                    - "position_marker": use this as a json object within the same object as within_function. The value 
                    of position marker can be at_start (insert to beginning of function scope), before_return (insert right before function return) or a position_marker = {after_line: <function_line_number>}. 
                    after_line uses the line numbers with the function name being line 0, etc. 
                    
               - "after_marker": a custom code marker or comment present in the file.
               - "global": to insert code at the global scope.
           - "new_content": the code to insert.
           - "indentation_hint": give an indentation hint. The options are relative to the previous line of code's indentation level. Options: maintain_indent, increase_indent, decrease_indent, no_hint
           - "sub_type": the type of code being added. Options include:
               - "FUNCTION": a complete new function implementation.
               - "BLOCK": lines of code added within an existing function or structure.
               - "COMMENT": inline documentation or comment updates.
        """
    ),
    "REPLACE": (
        """
        REPLACE: Replace an existing code block with new content.
           - "operation": "REPLACE"
           - "filename": the file to modify.
           - "target_type": the type of code to be replaced. Options include:
               - "FUNCTION": the entire function implementation.
               - "BLOCK": a specific block of code within a function.
               - "SIGNATURE": the function's declaration (parameters, return type, etc.).
               - "COMMENT": inline documentation or comment section.
           - "target_reference": an object that specifies the location of the code to be replaced.
                - function_name - name of the function
                - code_snippet (optional) - exact string match that should be removed.
           - "new_content": the replacement code.
        """
    ),
    "RENAME": (
        """
        RENAME: Change the name of an identifier and update its references.
           - "filename": the file to modify.
           - "operation": "RENAME"
           - "target_type": the type of identifier (e.g., "FUNCTION", "CLASS", "VARIABLE").
           - "old_name": the current name.
           - "new_name": the new name.
           - "update_references": (optional) a boolean indicating whether to update all occurrences of the identifier.
        """
    ),
    "NEW": (
        """
        NEW: Create a new file.
           - "operation": "NEW"
           - "filename": the path of the new file to create.
           - "new_content": the entire content of the new file.
        """
    )
}

async def request_code(terminal, change_instruction, file):
    op_type = change_instruction["operation_type"]
    operation_prompt = operation_promts[op_type]
    dev_msg = (
        f"""
        You are an expert software engineer and code reviewer and have been tasked with a simple one step operation. 
        Format your response as a JSON object with a "changes" key that contains an array of modifications. You may only 
        use the following operation to complete the task: {operation_prompt}
        
        Wrap your response in ```json and ``` markers. Use \\n for line breaks in new_content. 
        Do not include any additional commentary or explanation outside the JSON.
        """
    )

    prompt = (
        f"""
        You have been tasked with using the {op_type} operation to {change_instruction["description"]}. This should be 
        applied to the supplied file {change_instruction["filename"]} and you will need to locate the proper location in 
        the code to apply this change. The target location is {change_instruction["target_location"]}. Operations should 
        only be applied to this location, or else the task will fail.
        """
    )

    # construct and send message to LLM
    messages = []
    messages.append({"role": "system", "content": dev_msg})
    messages.append({"role": "user", "content": file})
    messages.append({"role": "user", "content": prompt})
    terminal.logger.info(f"Sending code request to {terminal.model}")
    terminal_print(f"\nSending code request to {terminal.model}...", PrintType.PROCESSING)

    follow_up_response = await stream_request(terminal, terminal.model, messages)
    terminal_print("", PrintType.INFO)
    terminal.messages[terminal.model].append({"role": "assistant", "content": follow_up_response})
    return follow_up_response


async def send_file_request(terminal, files_to_send, user_task, assistant_plan = None):
    terminal.logger.info(f"Detected file request: {files_to_send}")
    terminal_print(f"\nDetected file request: {files_to_send}", PrintType.INFO)

    files_content = get_file_contents(files_to_send)

    dev_msg = (
        """
        Instructions:
        You are a professor of computer science, currently teaching a basic CS1000 course to some new students with 
        little experience programming. The requested task is one that will be given to the students.
        CRITICAL: Do not provide any code for the students, only textual aide. 
        
        Generate a plan of discrete steps. The plan must be formatted as a numbered list where each step corresponds to a single operation (ADD, DELETE, REPLACE, 
        RENAME, or NEW). Each step should be self-contained and include:

        - The operation type.
        - Filename
        - The target location or reference (such as a function name, marker, or global scope).
        - A brief description of the intended change.
    
        Ensure that a student can follow each step independently. Provide only the plan in your response, with no 
        additional commentary or extraneous information. Some tasks for the students may be doable in a single step.
        
        The response should be in json format example: {"steps": [{"operation_type": "ADD", "filename": "src/test_file.py", "target_location": "after function X scope end", "description": "Adjust the code so that it prints hello world"}]}
        """
    )

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
    terminal.messages[terminal.model].append({"role": "assistant", "content": follow_up_response})

    return follow_up_response
