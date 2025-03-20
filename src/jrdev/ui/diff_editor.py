import os
import signal
import platform
import sys
from typing import List

# Import curses with Windows compatibility
try:
    import curses
except ImportError:
    if platform.system() == 'Windows':
        try:
            import windows_curses as curses
        except ImportError:
            # If windows_curses isn't installed, provide error message
            curses = None
    else:
        # If not Windows and curses isn't available, there's a problem
        curses = None


def disable_flow_control():
    """Disables flow control to allow Ctrl+S to work in some terminals."""
    if platform.system() != 'Windows':
        os.system("stty -ixon")


def curses_editor(content: List[str]) -> List[str]:
    """
    A simple curses-based text editor for editing content in the terminal.
    
    Features:
    - Regular editing mode for text modifications
    - Move mode (toggle with Ctrl+O) that allows:
      - Moving added lines (starting with '+') up and down with arrow keys
      - Adjusting indentation (add/remove spaces) with left/right arrow keys
    - Selection mode (activated in move mode with Ctrl+A):
      - Grey highlight shows selected lines
      - Arrow keys extend/shrink selection
      - W/S keys move selected lines up/down
      - A/D keys decrease/increase indentation
      - Cancel selection with Esc
    
    Args:
        content: List of strings representing each line of content to edit

    Returns:
        List of strings with the edited content
    """
    # Check if curses is available
    if curses is None:
        print("Error: The curses library is not available.")
        print("On Windows, install the windows-curses package: pip install windows-curses")
        return content
        
    result = []  # Default empty result in case of error

    def signal_handler(sig, frame):
        # Restore terminal settings if interrupted
        curses.endwin()
        exit(0)

    # Save the original signal handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal_handler)

    disable_flow_control()

    try:
        # Initialize the editor
        def editor(stdscr):
            nonlocal result
            # Clear the screen
            stdscr.clear()
            # Hide the cursor
            curses.curs_set(1)
            # Don't wait for input when getch() is called
            stdscr.nodelay(0)
            # Enable keypad mode
            stdscr.keypad(1)
            # Get screen dimensions
            height, width = stdscr.getmaxyx()

            # Initialize colors
            if curses.has_colors():
                curses.start_color()
                curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # For additions
                curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # For deletions
                curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)   # For status bar
                curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)  # For selected lines

            # Create a list of lines for the editor
            lines = content.copy()
            if not lines:
                lines = [""]

            # Editor state
            current_line = 0
            current_col = 0
            offset_y = 0   # Vertical scroll offset
            move_mode = False  # Flag for move mode
            selection_mode = False  # Flag for selection mode
            selection_start = None  # Start line for selection
            selected_lines = set()  # Set of selected line indices

            # Status messages
            status_message = "EDIT MODE | Ctrl+S or Alt+W: Save | Ctrl+Q, Alt+Q, or ESC: Quit | Ctrl+O: Toggle Move Mode | Arrows: Navigate"

            # Main editor loop
            while True:
                # Clear the screen
                stdscr.clear()

                # Calculate available display area (height - 1 for status bar)
                display_height = height - 1

                # Adjust vertical offset if needed to keep the cursor in view
                if current_line < offset_y:
                    offset_y = current_line
                if current_line >= offset_y + display_height:
                    offset_y = current_line - display_height + 1

                # Display the text with line numbers
                for i in range(min(display_height, len(lines))):
                    line_idx = i + offset_y
                    if line_idx < len(lines):
                        line = lines[line_idx]
                        # Line number
                        line_num = f"{line_idx + 1:4} "
                        stdscr.addstr(i, 0, line_num)

                        # Line content with color
                        line_idx = i + offset_y
                        
                        # Choose the appropriate color based on line type and selection status
                        if line_idx in selected_lines:
                            # Selected line gets the selection highlight
                            stdscr.addstr(i, 5, line[:width-6], curses.color_pair(4))
                        elif line.startswith("+"):
                            stdscr.addstr(i, 5, line[:width-6], curses.color_pair(1))
                        elif line.startswith("-"):
                            stdscr.addstr(i, 5, line[:width-6], curses.color_pair(2))
                        else:
                            stdscr.addstr(i, 5, line[:width-6])

                # Status bar
                if selection_mode and move_mode:
                    current_status = "SELECTION MODE | ↑↓: Extend Selection | W/S: Move Up/Down | A/D: Decrease/Increase Indent | Esc: Cancel | Ctrl+O: Exit"
                elif move_mode:
                    current_status = "MOVE MODE | ↑↓: Move Lines | ←→: Adjust Indentation | Ctrl+A: Select Lines | Ctrl+O: Exit Move Mode"
                else:
                    current_status = status_message
                
                if curses.has_colors():
                    stdscr.addstr(height-1, 0, current_status.ljust(width)[:width-1],
                                 curses.color_pair(3))
                else:
                    stdscr.addstr(height-1, 0, current_status.ljust(width)[:width-1],
                                 curses.A_REVERSE)

                # Position the cursor
                cursor_y = current_line - offset_y
                cursor_x = current_col + 5  # +5 for line number space
                if 0 <= cursor_y < display_height and 0 <= cursor_x < width:
                    stdscr.move(cursor_y, min(cursor_x, width-1))

                # Process key input
                key = stdscr.getch()

                # DEBUG: Show key code if F1 is pressed
                if key == curses.KEY_F1:
                    # Show detailed key information for debugging
                    debug_info = f"Key: {key}, Move mode: {move_mode}"
                    stdscr.addstr(0, 0, debug_info.ljust(width-1), curses.A_REVERSE)
                    stdscr.refresh()
                    stdscr.getch()  # Wait for another key press
                    continue

                # Toggle move mode with Ctrl+O
                if key == ord('o') - 96 or key == ord('O') - 64:  # Ctrl+O
                    move_mode = not move_mode
                    # Clear selection when exiting move mode
                    if not move_mode:
                        selection_mode = False
                        selected_lines.clear()
                        selection_start = None
                    continue
                
                # Universal control keys (work in both modes)
                if key == ord('s') - 96 or key == ord('S') - 64:  # Ctrl+S to save
                    result = lines
                    return
                elif key == ord('q') - 96 or key == ord('Q') - 64:  # Ctrl+Q to quit without saving
                    return
                elif key == ord('w') and (stdscr.inch(cursor_y, 0) & curses.A_ALTCHARSET):  # Alt+W to save
                    result = lines
                    return
                elif key == ord('q') and (stdscr.inch(cursor_y, 0) & curses.A_ALTCHARSET):  # Alt+Q to quit
                    return
                elif key == 27:  # ESC key
                    # Check if it's followed by another key (indicating arrow keys, etc)
                    stdscr.nodelay(True)
                    n = stdscr.getch()
                    stdscr.nodelay(False)
                    if n == -1:  # No other key, just ESC
                        return
                
                # Handle mode-specific keys
                elif move_mode:
                    # Only affect lines that start with '+'
                    is_added_line = False
                    if 0 <= current_line < len(lines) and lines[current_line].startswith('+'):
                        is_added_line = True
                    
                    # Enter selection mode with Ctrl+A
                    if key == ord('a') - 96 or key == ord('A') - 64:  # Ctrl+A to start selection
                        # Only allow selection mode if we're on an added line
                        if is_added_line:
                            selection_mode = True
                            selection_start = current_line
                            selected_lines = {current_line}
                    
                    # Selection mode handling
                    elif selection_mode:
                        if key == 27:  # ESC - cancel selection
                            selection_mode = False
                            selected_lines.clear()
                            selection_start = None
                        
                        elif (key == curses.KEY_UP) and current_line > 0:
                            # Move selection cursor up and update selection range
                            current_line -= 1
                            # Update selection if on a '+' line
                            if 0 <= current_line < len(lines) and lines[current_line].startswith('+'):
                                # Calculate selection range
                                if selection_start is not None:
                                    start = min(selection_start, current_line)
                                    end = max(selection_start, current_line)
                                    # Update selected lines
                                    selected_lines = {i for i in range(start, end + 1) 
                                                    if 0 <= i < len(lines) and lines[i].startswith('+')}
                        
                        elif (key == curses.KEY_DOWN) and current_line < len(lines) - 1:
                            # Move selection cursor down and update selection range
                            current_line += 1
                            # Update selection if on a '+' line
                            if 0 <= current_line < len(lines) and lines[current_line].startswith('+'):
                                # Calculate selection range
                                if selection_start is not None:
                                    start = min(selection_start, current_line)
                                    end = max(selection_start, current_line)
                                    # Update selected lines
                                    selected_lines = {i for i in range(start, end + 1) 
                                                    if 0 <= i < len(lines) and lines[i].startswith('+')}
                            
                        elif key == ord('a') or key == ord('A'):  # 'a' key - Decrease indent (outdent)
                            if selected_lines:
                                for idx in selected_lines:
                                    if lines[idx].startswith('+') and lines[idx][1:].startswith(' '):
                                        lines[idx] = lines[idx][0] + lines[idx][2:]
                        
                        elif key == ord('d') or key == ord('D'):  # 'd' key - Increase indent
                            if selected_lines:
                                for idx in selected_lines:
                                    if lines[idx].startswith('+'):
                                        lines[idx] = lines[idx][0] + ' ' + lines[idx][1:]
                        
                        elif key == ord('w') or key == ord('W'):  # 'w' key - Move selection up
                            if selected_lines:
                                # Sort selected lines
                                selected_indices = sorted(selected_lines)
                                
                                # Move lines as a block up
                                if min(selected_indices) > 1:
                                    # Move entire block up
                                    target_index = min(selected_indices) - 1
                                    # Check if target is a '+' line or not
                                    if not lines[target_index].startswith('+'):
                                        # Find the next '+' line above 
                                        for i in range(target_index, -1, -1):
                                            if lines[i].startswith('+'):
                                                target_index = i
                                                break
                                        
                                    # Swap the line above with the first selected line
                                    temp_line = lines[target_index]
                                    # Shift all selected lines up by one
                                    for i in range(len(selected_indices)):
                                        if i == 0:
                                            lines[target_index] = lines[selected_indices[i]]
                                        else:
                                            lines[selected_indices[i-1]] = lines[selected_indices[i]]
                                    lines[selected_indices[-1]] = temp_line
                                    
                                    # Update selection indices
                                    new_selected = {idx - 1 for idx in selected_indices if idx - 1 >= 0}
                                    selected_lines = new_selected
                                    selection_start = min(new_selected) if new_selected else None
                                    current_line = min(new_selected) if new_selected else current_line - 1
                        
                        elif key == ord('s') or key == ord('S'):  # 's' key - Move selection down
                            if selected_lines:
                                # Sort selected lines in reverse for moving down
                                selected_indices = sorted(selected_lines, reverse=True)
                                
                                # Move lines as a block down
                                if max(selected_indices) < len(lines) - 1:
                                    # Move entire block down
                                    target_index = max(selected_indices) + 1
                                    # Check if target is a '+' line or not
                                    if not lines[target_index].startswith('+'):
                                        # Find the next '+' line below
                                        for i in range(target_index, len(lines)):
                                            if lines[i].startswith('+'):
                                                target_index = i
                                                break
                                        
                                    # Swap the line below with the last selected line
                                    temp_line = lines[target_index]
                                    # Shift all selected lines down by one
                                    for i in range(len(selected_indices)):
                                        if i == 0:
                                            lines[target_index] = lines[selected_indices[i]]
                                        else:
                                            lines[selected_indices[i-1]] = lines[selected_indices[i]]
                                    lines[selected_indices[-1]] = temp_line
                                    
                                    # Update selection indices
                                    new_selected = {idx + 1 for idx in selected_indices if idx + 1 < len(lines)}
                                    selected_lines = new_selected
                                    selection_start = max(new_selected) if new_selected else None
                                    current_line = max(new_selected) if new_selected else current_line + 1
                    
                    # Regular move mode operations (when not in selection mode)
                    elif key == curses.KEY_UP and current_line > 0 and is_added_line:
                        # Move the current line up by swapping with the line above
                        if current_line > 1:  # Ensure there's a line above to swap with
                            lines[current_line], lines[current_line-1] = lines[current_line-1], lines[current_line]
                            current_line -= 1
                    elif key == curses.KEY_DOWN and current_line < len(lines) - 1 and is_added_line:
                        # Move the current line down by swapping with the line below
                        lines[current_line], lines[current_line+1] = lines[current_line+1], lines[current_line]
                        current_line += 1
                    # Also handle standard movement in move mode for navigation
                    elif key == curses.KEY_UP and current_line > 0 and not is_added_line:
                        current_line -= 1
                    elif key == curses.KEY_DOWN and current_line < len(lines) - 1 and not is_added_line:
                        current_line += 1
                    elif key == curses.KEY_LEFT and is_added_line and not selection_mode:
                        # Remove whitespace at the beginning of the line (after the '+')
                        if len(lines[current_line]) > 1 and lines[current_line][1:].startswith(' '):
                            lines[current_line] = lines[current_line][0] + lines[current_line][2:]
                    elif key == curses.KEY_RIGHT and is_added_line and not selection_mode:
                        # Add whitespace at the beginning of the line (after the '+')
                        lines[current_line] = lines[current_line][0] + ' ' + lines[current_line][1:]
                else:
                    # Edit mode keys
                    if key == curses.KEY_UP and current_line > 0:
                        current_line -= 1
                        current_col = min(current_col, len(lines[current_line]))
                    elif key == curses.KEY_DOWN and current_line < len(lines) - 1:
                        current_line += 1
                        current_col = min(current_col, len(lines[current_line]))
                    elif key == curses.KEY_LEFT and current_col > 0:
                        current_col -= 1
                    elif key == curses.KEY_RIGHT and current_col < len(lines[current_line]):
                        current_col += 1
                    elif key == curses.KEY_HOME:
                        current_col = 0
                    elif key == curses.KEY_END:
                        current_col = len(lines[current_line])
                    elif key == curses.KEY_PPAGE:  # Page Up
                        current_line = max(0, current_line - display_height)
                        current_col = min(current_col, len(lines[current_line]))
                    elif key == curses.KEY_NPAGE:  # Page Down
                        current_line = min(len(lines) - 1, current_line + display_height)
                        current_col = min(current_col, len(lines[current_line]))
                    elif key == 10:  # Enter/Return
                        # Split the line
                        new_line = lines[current_line][current_col:]
                        lines[current_line] = lines[current_line][:current_col]
                        lines.insert(current_line + 1, new_line)
                        current_line += 1
                        current_col = 0
                    elif key == curses.KEY_BACKSPACE or key == 127:  # Backspace
                        if current_col > 0:
                            # Delete the character before the cursor
                            lines[current_line] = lines[current_line][:current_col-1] + lines[current_line][current_col:]
                            current_col -= 1
                        elif current_line > 0:
                            # Join with the previous line
                            current_col = len(lines[current_line - 1])
                            lines[current_line - 1] += lines[current_line]
                            lines.pop(current_line)
                            current_line -= 1
                    elif key == curses.KEY_DC:  # Delete
                        if current_col < len(lines[current_line]):
                            # Delete the character at the cursor
                            lines[current_line] = lines[current_line][:current_col] + lines[current_line][current_col+1:]
                        elif current_line < len(lines) - 1:
                            # Join with the next line
                            lines[current_line] += lines[current_line + 1]
                            lines.pop(current_line + 1)
                    elif 32 <= key <= 126:  # Printable ASCII chars
                        # Insert the character at the cursor position
                        ch = chr(key)
                        lines[current_line] = lines[current_line][:current_col] + ch + lines[current_line][current_col:]
                        current_col += 1

        # Run the editor
        curses.wrapper(editor)
        return result or content  # Return the edited content or original if empty

    finally:
        # Restore the original signal handler
        signal.signal(signal.SIGINT, original_sigint)
        # Ensure terminal is reset
        try:
            curses.endwin()
        except:
            pass