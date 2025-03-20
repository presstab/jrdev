import curses
import os
import signal
from typing import List


def disable_flow_control():
    """Disables flow control to allow Ctrl+S to work in some terminals."""
    os.system("stty -ixon")


def curses_editor(content: List[str]) -> List[str]:
    """
    A simple curses-based text editor for editing content in the terminal.

    Args:
        content: List of strings representing each line of content to edit

    Returns:
        List of strings with the edited content
    """
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

            # Create a list of lines for the editor
            lines = content.copy()
            if not lines:
                lines = [""]

            # Editor state
            current_line = 0
            current_col = 0
            offset_y = 0   # Vertical scroll offset

            # Status messages
            status_message = "EDIT MODE | Ctrl+S or Alt+W: Save | Ctrl+Q, Alt+Q, or ESC: Quit | Arrows: Navigate"

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
                        if line.startswith("+"):
                            stdscr.addstr(i, 5, line[:width-6], curses.color_pair(1))
                        elif line.startswith("-"):
                            stdscr.addstr(i, 5, line[:width-6], curses.color_pair(2))
                        else:
                            stdscr.addstr(i, 5, line[:width-6])

                # Status bar
                if curses.has_colors():
                    stdscr.addstr(height-1, 0, status_message.ljust(width)[:width-1],
                                 curses.color_pair(3))
                else:
                    stdscr.addstr(height-1, 0, status_message.ljust(width)[:width-1],
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
                    stdscr.addstr(0, width - 20, f"Key: {key}    ", curses.A_REVERSE)
                    stdscr.refresh()
                    stdscr.getch()  # Wait for another key press

                # Navigation keys
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

                # Editing keys
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

                # Control keys
                elif key == ord('s') - 96 or key == ord('S') - 64:  # Ctrl+S to save
                    result = lines
                    return
                elif key == ord('q') - 96 or key == ord('Q') - 64:  # Ctrl+Q to quit without saving
                    return
                # Alternative keys for save/quit (more reliable across terminals)
                elif key == ord('w') and (stdscr.inch(cursor_y, 0) & curses.A_ALTCHARSET):  # Alt+W to save
                    result = lines
                    return
                elif key == ord('q') and (stdscr.inch(cursor_y, 0) & curses.A_ALTCHARSET):  # Alt+Q to quit
                    return
                # Add ESC key as another way to exit
                elif key == 27:  # ESC key
                    # Check if it's followed by another key (indicating arrow keys, etc)
                    stdscr.nodelay(True)
                    n = stdscr.getch()
                    stdscr.nodelay(False)
                    if n == -1:  # No other key, just ESC
                        return

                # Regular characters
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