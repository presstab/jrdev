#!/usr/bin/env python3

"""
UI utilities for JrDev terminal interface.
"""

import logging
import platform
import threading
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# Initialize colorama for Windows terminal color support
if platform.system() == 'Windows':
    try:
        import colorama
        colorama.init()
    except ImportError:
        # If colorama isn't installed, colors may not work correctly on Windows
        pass

# Get the global logger instance
logger = logging.getLogger("jrdev")


class PrintType(Enum):
    """Types of terminal output with different formatting."""
    INFO = auto()        # General information
    ERROR = auto()       # Error messages
    PROCESSING = auto()  # Processing/loading indicators
    LLM = auto()         # AI model responses
    USER = auto()        # User input echoing
    SUCCESS = auto()     # Success messages
    WARNING = auto()     # Warning messages
    COMMAND = auto()     # Command output
    HEADER = auto()      # Headers/titles
    SUBHEADER = auto()   # Category headers

def printtype_to_string(print_type: PrintType):
    mapping = {
        PrintType.INFO: "INFO",
        PrintType.ERROR: "ERROR",
        PrintType.PROCESSING: "PROCESSING",
        PrintType.LLM: "LLM",
        PrintType.USER: "USER",
        PrintType.SUCCESS: "SUCCESS",
        PrintType.WARNING: "WARNING",
        PrintType.COMMAND: "COMMAND",
        PrintType.HEADER: "HEADER",
        PrintType.SUBHEADER: "SUBHEADER"
    }
    return mapping.get(print_type, f"UNKNOWN_{print_type}")


# ANSI color codes
COLORS: Dict[str, str] = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "ITALIC": "\033[3m",
    "UNDERLINE": "\033[4m",
    "BLACK": "\033[30m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "MAGENTA": "\033[35m",
    "CYAN": "\033[36m",
    "WHITE": "\033[37m",
    "BRIGHT_BLACK": "\033[90m",
    "BRIGHT_RED": "\033[91m",
    "BRIGHT_GREEN": "\033[92m",
    "BRIGHT_YELLOW": "\033[93m",
    "BRIGHT_BLUE": "\033[94m",
    "BRIGHT_MAGENTA": "\033[95m",
    "BRIGHT_CYAN": "\033[96m",
    "BRIGHT_WHITE": "\033[97m",
}


# Mapping print types to their formatting
FORMAT_MAP: Dict[PrintType, str] = {
    PrintType.INFO: COLORS["BRIGHT_WHITE"],
    PrintType.ERROR: COLORS["BRIGHT_RED"],
    PrintType.PROCESSING: COLORS["BRIGHT_CYAN"] + COLORS["DIM"],
    PrintType.LLM: COLORS["BRIGHT_GREEN"],
    PrintType.USER: COLORS["BRIGHT_YELLOW"],
    PrintType.SUCCESS: COLORS["BRIGHT_GREEN"] + COLORS["BOLD"],
    PrintType.WARNING: COLORS["BRIGHT_YELLOW"] + COLORS["BOLD"],
    PrintType.COMMAND: COLORS["BRIGHT_BLUE"] + COLORS["BOLD"],
    PrintType.HEADER: (COLORS["BRIGHT_WHITE"] + COLORS["BOLD"] +
                        COLORS["UNDERLINE"]),
    PrintType.SUBHEADER: COLORS["BRIGHT_WHITE"] + COLORS["BOLD"],
}


def terminal_print(
    message: Any,
    print_type: PrintType = PrintType.INFO,
    end: str = "\n",
    prefix: Optional[str] = None,
    flush: bool = False
) -> None:
    """
    Print formatted text to the terminal with color coding based on the message type.
    If the execution is not in the main thread, log the message instead.

    Args:
        message: The message to print
        print_type: The type of message (determines formatting)
        end: The end character (default: newline)
        prefix: Optional prefix to add before the message
        flush: Whether to flush the output (useful for streaming outputs)
    """
    # Check if we're in the main thread
    # if threading.current_thread() is not threading.main_thread():
    #     # Not in main thread, log the message instead
    #     logger = logging.getLogger("jrdev")
    #
    #     # Determine log level based on print_type
    #     if print_type == PrintType.ERROR:
    #         logger.error(message)
    #     elif print_type == PrintType.WARNING:
    #         logger.warning(message)
    #     elif print_type == PrintType.SUCCESS:
    #         logger.info(f"SUCCESS: {message}")
    #     else:
    #         logger.info(message)
    #     return
    # In main thread, print to terminal as usual
    format_code = FORMAT_MAP.get(print_type, COLORS["RESET"])
    formatted_prefix = f"{format_code}{prefix} " if prefix else format_code

    print_str = f"{formatted_prefix}{message}{COLORS['RESET']}"
    print(print_str, end=end, flush=flush)


def display_diff(app: Any, diff_lines: List[str]) -> None:
    """
    Display a unified diff to the terminal with color-coded additions and deletions.

    Args:
        app: Application instance
        diff_lines: List of lines from a unified diff
    """
    if not diff_lines:
        app.ui.print_text("No changes detected in file content.", PrintType.WARNING)
        return

    app.ui.print_text("File changes diff:", PrintType.HEADER)
    for line in diff_lines:
        if line.startswith('+'):
            app.ui.print_text(line.rstrip(), PrintType.SUCCESS)
        elif line.startswith('-'):
            app.ui.print_text(line.rstrip(), PrintType.ERROR)
        else:
            app.ui.print_text(line.rstrip())


def print_steps(app: Any, steps: Dict[str, Any], completed_steps: List[int], current_step: Optional[int] = None) -> None:
    """
    Print steps in the form of a colorful todo list with check marks for completed steps
    and highlighting for the current step being worked on.

    Args:
        app: The Application instance
        steps: Dictionary containing the steps to print
        completed_steps: Optional list of step indices (0-based) that have been completed
        current_step: Optional index (0-based) of the current step being worked on
    """

    if app.ui.ui_name == "textual":
        print_steps_plain(app, steps, completed_steps, current_step)
        return

    # Define operation type colors
    operation_colors = {
        "ADD": COLORS["BRIGHT_GREEN"],
        "NEW": COLORS["BRIGHT_CYAN"],
        "DELETE": COLORS["BRIGHT_RED"],
        "REPLACE": COLORS["BRIGHT_YELLOW"],
        # Default color for unknown operations
        "DEFAULT": COLORS["BRIGHT_MAGENTA"]
    }
    
    if "steps" not in steps or not steps["steps"]:
        app.ui.print_text("No steps to display", PrintType.WARNING)
        return
    
    if completed_steps is None:
        completed_steps = []
    
    app.ui.print_text("\n📋 TODO List:", PrintType.HEADER)
    
    for i, step in enumerate(steps["steps"], 1):
        # Get step details with fallbacks
        operation = step.get("operation_type", "UNKNOWN")
        filename = step.get("filename", "UNKNOWN")
        description = step.get("description", "No description provided")
        target = step.get("target_location", "UNKNOWN")
        
        # Get color for operation type (with fallback to DEFAULT)
        op_color = operation_colors.get(operation, operation_colors["DEFAULT"])
        
        # Determine step status and formatting
        step_idx = i - 1  # Convert to 0-based index
        
        if step_idx in completed_steps:
            # Completed step
            checkbox = f"{COLORS['BRIGHT_GREEN']}✓{COLORS['RESET']}"
            status_color = COLORS["BRIGHT_GREEN"]
            status_prefix = ""
            status_suffix = ""
        elif step_idx == current_step:
            # Current step being worked on
            checkbox = "▶"
            status_color = COLORS["BRIGHT_YELLOW"]
            status_prefix = f"{COLORS['BRIGHT_YELLOW']}⟩ "
            status_suffix = f" ⟨{COLORS['RESET']}"
        else:
            # Pending step
            checkbox = "□"
            status_color = COLORS["RESET"]
            status_prefix = ""
            status_suffix = ""
        
        # Print step with colored operation type and appropriate checkbox
        step_prefix = f"{status_prefix}{checkbox} {i}. "
        operation_formatted = f"{op_color}{operation}{COLORS['RESET']}"
        
        app.ui.print_text(
            f"{status_color}{step_prefix}{COLORS['RESET']}{operation_formatted}: "
            f"{COLORS['BOLD']}{filename}{COLORS['RESET']} - {description}{status_suffix}",
            PrintType.INFO
        )
        
        # Print target location with indentation
        location_indent = "   "
        if step_idx == current_step:
            location_indent = "   ┃ "
            
        app.ui.print_text(
            f"{location_indent}{COLORS['DIM']}Location: {target}{COLORS['RESET']}",
            PrintType.INFO
        )
    
    app.ui.print_text("", PrintType.INFO)  # Add an empty line after the list

def print_steps_plain(app: Any, steps: Dict[str, Any], completed_steps: Optional[List[int]] = None, current_step: Optional[int] = None) -> None:
    """
    Print steps in plain text format without any colors or emoticons.

    Args:
        app: The Application instance
        steps: Dictionary containing the steps to print
        completed_steps: Optional list of step indices (0-based) that have been completed
        current_step: Optional index (0-based) of the current step being worked on
    """
    if "steps" not in steps or not steps["steps"]:
        app.ui.print_text("No steps to display", PrintType.INFO)
        return

    if completed_steps is None:
        completed_steps = []

    app.ui.print_text("\nTODO List:", PrintType.INFO)

    for i, step in enumerate(steps["steps"], 1):
        operation = step.get("operation_type", "UNKNOWN")
        filename = step.get("filename", "UNKNOWN")
        description = step.get("description", "No description provided")
        target = step.get("target_location", "UNKNOWN")

        step_idx = i - 1  # Convert to 0-based index

        if step_idx in completed_steps:
            checkbox = "x"
        elif step_idx == current_step:
            checkbox = ">"
        else:
            checkbox = "-"

        step_prefix = f"{checkbox} {i}. "
        app.ui.print_text(
            f"{step_prefix}{operation}: {filename} - {description}",
            PrintType.INFO
        )

        location_indent = "   "
        app.ui.print_text(
            f"{location_indent}Location: {target}",
            PrintType.INFO
        )

    app.ui.print_text("", PrintType.INFO)  # Add an empty line after the list

async def prompt_for_confirmation(app: Any, prompt_text: str = "Apply these changes?", diff_lines: Optional[List[str]] = None) -> Tuple[str, Optional[str]]:
    """
    Prompt the user for confirmation with options to apply, reject, request changes,
    or edit the changes in a text editor.
    
    This is a backward compatibility wrapper that delegates to the UI wrapper's implementation.

    Args:
        app: The application instance
        prompt_text: The text to display when prompting the user
        diff_lines: Optional list of diff lines to display

    Returns:
        Tuple of (response, message):
            - response: 'yes', 'no', 'request_change', or 'edit'
            - message: User's feedback message when requesting changes,
                      or edited content when editing, None otherwise
    """
    # Delegate to the app's UI implementation
    return await app.ui.prompt_for_confirmation(prompt_text, diff_lines)


def show_conversation(app: Any, max_messages: int = 10) -> None:
    """
    Display the conversation history for the current thread with color coding.
    
    Args:
        app: The application instance
        max_messages: Maximum number of messages to display
    """
    # Get the current thread
    current_thread = app.get_current_thread()
    thread_id = app.state.active_thread
    
    # Show thread header with ID
    app.ui.print_text(f"\n💬 Thread: {thread_id}", PrintType.HEADER)
    
    # Get messages from the thread
    messages = current_thread.messages
    
    # If no messages, show empty message
    if not messages:
        app.ui.print_text("No messages in this thread yet.", PrintType.INFO)
        return
    
    # Get the last N messages
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    # Show message count
    if len(messages) > max_messages:
        app.ui.print_text(f"Showing last {max_messages} of {len(messages)} messages", PrintType.INFO)
    
    # Display message divider
    app.ui.print_text("───────────────────────────────────────────", PrintType.INFO)
    
    # Display each message
    for idx, msg in enumerate(recent_messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # Truncate long messages for display
        max_preview_len = 100
        preview = content[:max_preview_len]
        if len(content) > max_preview_len:
            preview += "..."
        
        # Format based on role
        if role == "system":
            app.ui.print_text(f"🔧 System:", PrintType.SUBHEADER)
            app.ui.print_text(f"   {preview}", PrintType.INFO)
        elif role == "user":
            app.ui.print_text(f"👤 You:", PrintType.SUBHEADER)
            app.ui.print_text(f"   {preview}", PrintType.USER)
        elif role == "assistant":
            app.ui.print_text(f"🤖 Assistant:", PrintType.SUBHEADER)
            app.ui.print_text(f"   {preview}", PrintType.LLM)
        else:
            app.ui.print_text(f"[{role}]", PrintType.SUBHEADER)
            app.ui.print_text(f"   {preview}", PrintType.INFO)
        
        # Add separator between messages except for the last one
        if idx < len(recent_messages) - 1:
            app.ui.print_text("   · · ·", PrintType.INFO)
