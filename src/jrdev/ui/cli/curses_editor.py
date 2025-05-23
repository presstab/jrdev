#!/usr/bin/env python3

"""
A simple curses-based text editor for editing multi-line text.
Provides basic navigation, editing capabilities, and save/cancel options.
"""

import curses
from typing import Optional, Tuple


class CursesEditor:
    """A simple curses-based text editor for multi-line text editing."""

    def __init__(self, initial_text: str = ""):
        """Initialize the editor with optional initial text."""
        self.lines = initial_text.split('\n') if initial_text else [""]
        self.cursor_y = 0  # Current line
        self.cursor_x = 0  # Current column
        self.scroll_y = 0  # Vertical scroll position
        self.scroll_x = 0  # Horizontal scroll position
        self.status_message = "Alt+S: Save | Alt+Q/ESC: Cancel | Arrow keys: Navigate"
        self.saved_text = None
        self.cancelled = False

    def run(self) -> Tuple[bool, Optional[str]]:
        """Run the editor and return (success, edited_text)."""
        try:
            # Initialize curses
            stdscr = curses.initscr()
            curses.noecho()  # Don't echo keypresses
            curses.cbreak()  # React to keys without Enter
            curses.start_color()  # Enable color support
            curses.use_default_colors()  # Use terminal's default colors
            stdscr.keypad(True)  # Enable special keys

            # Set up color pairs
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Status bar
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected text

            # Main editor loop
            while True:
                # Get terminal dimensions
                max_y, max_x = stdscr.getmaxyx()
                editor_height = max_y - 2  # Reserve bottom line for status

                # Clear screen
                stdscr.clear()

                # Adjust scroll position if cursor is outside visible area
                if self.cursor_y < self.scroll_y:
                    self.scroll_y = self.cursor_y
                if self.cursor_y >= self.scroll_y + editor_height:
                    self.scroll_y = self.cursor_y - editor_height + 1
                if self.cursor_x < self.scroll_x:
                    self.scroll_x = self.cursor_x
                if self.cursor_x >= self.scroll_x + max_x - 5:  # Account for line number width
                    self.scroll_x = self.cursor_x - max_x + 6  # +5 to account for line number width and buffer

                # Display text with line numbers
                for y in range(editor_height):
                    file_line = y + self.scroll_y
                    if file_line >= len(self.lines):
                        break

                    # Display line number
                    line_num = f"{file_line + 1:3d} "
                    stdscr.addstr(y, 0, line_num)

                    # Display line content
                    line = self.lines[file_line]
                    display_line = line[self.scroll_x:self.scroll_x + max_x - 5]
                    stdscr.addstr(y, 4, display_line)

                # Display status bar
                status_bar = self.status_message
                position_info = f" | Line: {self.cursor_y + 1}/{len(self.lines)} Col: {self.cursor_x + 1}"
                status_bar = status_bar + position_info
                status_bar = status_bar[:max_x - 1]
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(max_y - 1, 0, status_bar.ljust(max_x - 1))
                stdscr.attroff(curses.color_pair(1))

                # Position cursor
                cursor_screen_y = self.cursor_y - self.scroll_y
                cursor_screen_x = self.cursor_x - self.scroll_x + 4  # +4 for line number width
                if 0 <= cursor_screen_y < editor_height and 4 <= cursor_screen_x < max_x:
                    stdscr.move(cursor_screen_y, cursor_screen_x)

                # Refresh screen
                stdscr.refresh()

                # Handle keypresses
                try:
                    key = stdscr.getch()
                except KeyboardInterrupt:
                    self.cancelled = True
                    break

                if key == curses.KEY_UP:
                    self.move_cursor_up()
                elif key == curses.KEY_DOWN:
                    self.move_cursor_down()
                elif key == curses.KEY_LEFT:
                    self.move_cursor_left()
                elif key == curses.KEY_RIGHT:
                    self.move_cursor_right()
                elif key == curses.KEY_HOME:
                    self.cursor_x = 0
                elif key == curses.KEY_END:
                    self.cursor_x = len(self.lines[self.cursor_y])
                elif key == curses.KEY_PPAGE:  # Page Up
                    self.cursor_y = max(0, self.cursor_y - editor_height)
                    self.scroll_y = max(0, self.scroll_y - editor_height)
                elif key == curses.KEY_NPAGE:  # Page Down
                    self.cursor_y = min(len(self.lines) - 1, self.cursor_y + editor_height)
                    self.scroll_y = min(len(self.lines) - 1, self.scroll_y + editor_height)
                elif key == ord('\n') or key == 10 or key == 13:  # Enter
                    self.insert_newline()
                elif key == 127 or key == curses.KEY_BACKSPACE:  # Backspace
                    self.handle_backspace()
                elif key == curses.KEY_DC:  # Delete
                    self.handle_delete()
                elif key == 9:  # Tab
                    self.insert_text("    ")  # 4 spaces for tab
                elif key == 27:  # ESC key (could be Alt combination or just ESC)
                    # Wait for another character
                    stdscr.nodelay(True) # Don't block for the next key
                    try:
                        next_key = stdscr.getch()
                        if next_key == ord('s') or next_key == ord('S'):  # Alt+S (save)
                            self.saved_text = '\n'.join(self.lines)
                            break
                        elif next_key == ord('q') or next_key == ord('Q'):  # Alt+Q (cancel)
                            self.cancelled = True
                            break
                        elif next_key == -1: # No other key followed ESC (plain ESC)
                            self.cancelled = True
                            break
                        # If another key followed that wasn't s/S or q/Q, it might be part of an escape sequence
                        # or an unhandled Alt combination. We can choose to ignore or handle further.
                        # For now, treat as cancel if not a save/quit Alt combo.
                        else:
                            # To be safe, if it's not a recognized Alt combo, assume it was just ESC for cancel.
                            # However, this might interfere with some terminal escape sequences if not handled carefully.
                            # A more robust solution would involve a timeout or more complex escape sequence parsing.
                            self.cancelled = True # Default to cancel for unrecognized sequences starting with ESC
                            break
                    except Exception: # Includes curses.error if getch fails in nodelay mode
                        self.cancelled = True # If any error during Alt key check, cancel
                        break
                    finally:
                        stdscr.nodelay(False) # Restore blocking mode

                elif key == ord('\x11') or key == 17:  # Ctrl+Q (cancel)
                    self.cancelled = True
                    break
                elif 32 <= key <= 126:  # Printable ASCII characters
                    self.insert_text(chr(key))

            # # Before saving, clean up self.lines to reduce consecutive empty lines to single empty lines.
            # # This addresses issues where editing might inadvertently create multiple empty lines
            # # when only one (or none) was intended, especially in diffs.
            # if not self.cancelled and self.lines:
            #     cleaned_lines_temp = []
            #     if self.lines: # Ensure self.lines is not empty
            #         cleaned_lines_temp.append(self.lines[0])
            #         for i in range(1, len(self.lines)):
            #             # Only add line if it's not an empty string immediately following another empty string
            #             if not (self.lines[i] == "" and cleaned_lines_temp[-1] == ""):
            #                 cleaned_lines_temp.append(self.lines[i])
            #     self.lines = cleaned_lines_temp
            
            if not self.cancelled:
                 self.saved_text = '\n'.join(self.lines)

            return (not self.cancelled, self.saved_text)

        finally:
            # Clean up curses
            if 'stdscr' in locals():
                stdscr.keypad(False)
            curses.nocbreak()
            curses.echo()
            curses.endwin()

    def move_cursor_up(self):
        """Move cursor up one line."""
        if self.cursor_y > 0:
            self.cursor_y -= 1
            # Adjust x position if new line is shorter
            self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))

    def move_cursor_down(self):
        """Move cursor down one line."""
        if self.cursor_y < len(self.lines) - 1:
            self.cursor_y += 1
            # Adjust x position if new line is shorter
            self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))

    def move_cursor_left(self):
        """Move cursor left one character."""
        if self.cursor_x > 0:
            self.cursor_x -= 1
        elif self.cursor_y > 0:  # Move to end of previous line
            self.cursor_y -= 1
            self.cursor_x = len(self.lines[self.cursor_y])

    def move_cursor_right(self):
        """Move cursor right one character."""
        if self.cursor_x < len(self.lines[self.cursor_y]):
            self.cursor_x += 1
        elif self.cursor_y < len(self.lines) - 1:  # Move to start of next line
            self.cursor_y += 1
            self.cursor_x = 0

    def insert_text(self, text: str):
        """Insert text at current cursor position."""
        current_line = self.lines[self.cursor_y]
        new_line = current_line[:self.cursor_x] + text + current_line[self.cursor_x:]
        self.lines[self.cursor_y] = new_line
        self.cursor_x += len(text)

    def insert_newline(self):
        """Insert a new line at current cursor position."""
        current_line = self.lines[self.cursor_y]
        self.lines[self.cursor_y] = current_line[:self.cursor_x]
        self.lines.insert(self.cursor_y + 1, current_line[self.cursor_x:])
        self.cursor_y += 1
        self.cursor_x = 0

    def handle_backspace(self):
        """Handle backspace key."""
        if self.cursor_x > 0:  # Not at start of line
            current_line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = current_line[:self.cursor_x - 1] + current_line[self.cursor_x:]
            self.cursor_x -= 1
        elif self.cursor_y > 0:  # At start of line but not first line
            # Merge with previous line
            prev_line_length = len(self.lines[self.cursor_y - 1])
            self.lines[self.cursor_y - 1] += self.lines[self.cursor_y]
            self.lines.pop(self.cursor_y)
            self.cursor_y -= 1
            self.cursor_x = prev_line_length
        # If it's the first line and cursor_x is 0, do nothing.
        # Also ensure self.lines is not empty or only contains one empty string that can't be further reduced by backspace.
        elif len(self.lines) == 1 and self.lines[0] == "":
            pass # Cannot backspace further

    def handle_delete(self):
        """Handle delete key."""
        current_line = self.lines[self.cursor_y]
        if self.cursor_x < len(current_line):  # Not at end of line
            self.lines[self.cursor_y] = current_line[:self.cursor_x] + current_line[self.cursor_x + 1:]
        elif self.cursor_y < len(self.lines) - 1:  # At end of line but not last line
            # Merge with next line
            self.lines[self.cursor_y] += self.lines[self.cursor_y + 1]
            self.lines.pop(self.cursor_y + 1)
        # If it's the last line and cursor is at the end, or if the line is empty, do nothing.
        elif len(self.lines) == 1 and self.lines[0] == "" and self.cursor_x == 0:
            pass # Cannot delete further


def is_curses_available() -> bool:
    """Check if curses is available on the current platform."""
    try:
        curses.initscr()
        curses.endwin()
        return True
    except Exception:
        return False


def edit_text(initial_text: str = "") -> Tuple[bool, Optional[str]]:
    """Edit text using the curses editor.
    
    Args:
        initial_text: The initial text to edit
        
    Returns:
        Tuple of (success, edited_text):
            - success: True if saved, False if cancelled
            - edited_text: The edited text if saved, None if cancelled
    """
    if not is_curses_available():
        print("Curses is not available on this platform.")
        return False, None
        
    editor = CursesEditor(initial_text)
    return editor.run()


if __name__ == "__main__":
    # Test the editor with some sample text
    sample_text = """This is a test of the curses editor.
It supports multiple lines.
You can navigate with arrow keys.
Press Ctrl+S to save or Ctrl+Q to cancel."""
    
    success, result = edit_text(sample_text)
    
    if success:
        print("Edited text:")
        print(result)
    else:
        print("Editing was cancelled.")
