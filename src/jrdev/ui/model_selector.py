#!/usr/bin/env python3

"""
Interactive model selector UI components for JrDev terminal.
"""
from typing import Any, List, Dict

# Import curses with Windows compatibility
try:
    import curses
    CURSES_AVAILABLE = True
except ImportError:
    curses = None
    CURSES_AVAILABLE = False

from jrdev.models.model_utils import Price_Per_Token_Scale
from jrdev.ui.ui import PrintType


async def text_based_model_selector(app: Any, models: List[Dict[str, Any]]) -> None:
    """
    Text-based model selector for systems without curses support.

    Args:
        app: The Application instance
        models: List of models to display
    """
    # Get token dollar value for cost calculations
    price_per_token_scale = Price_Per_Token_Scale()

    # Print header
    app.ui.print_text("\nAvailable Models:", print_type=PrintType.HEADER)
    app.ui.print_text(f"{'#':<3} | {'Model':<20} | {'Provider':<10} | {'Type':<10} | {'Input Cost':<12} | {'Output Cost':<12} | {'Context':<10}")
    app.ui.print_text("-" * 90)

    # Print models with index numbers
    for i, model in enumerate(models):
        # Extract model data
        model_name = model["name"]
        provider = model["provider"]
        is_think = model["is_think"]
        input_cost = model["input_cost"]
        output_cost = model["output_cost"]
        context_tokens = model["context_tokens"]

        # Format strings
        think_status = "Reasoning" if is_think else "Standard"
        input_cost_str = f"${input_cost/price_per_token_scale:.3f}/M"
        output_cost_str = f"${output_cost/price_per_token_scale:.3f}/M"
        context_str = f"{context_tokens//1024}K"

        # Truncate long model names
        display_name = model_name
        if len(model_name) > 20:
            display_name = model_name[:17] + "..."

        # Add indicator for current model
        indicator = ""
        if model_name == app.state.model:
            indicator = "* "

        app.ui.print_text(f"{i+1:<3} | {indicator}{display_name:<20} | {provider:<10} | {think_status:<10} | {input_cost_str:<12} | {output_cost_str:<12} | {context_str:<10}")

    # Prompt for selection
    app.ui.print_text("\nCurrent model: " + app.state.model)
    app.ui.print_text("\nSelect a new model using /model <model_name>")


def interactive_model_selector(stdscr, app, models):
    """
    Interactive model selector using curses.

    Args:
        stdscr: The curses standard screen
        app: The Application instance
        models: List of models to display

    Returns:
        Selected model name or None if cancelled
    """
    # Store selected model
    selected_model = None

    # Setup curses
    try:
        # Basic setup
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)  # Enable special keys

        # Use default terminal colors for transparency
        if hasattr(curses, 'use_default_colors'):
            curses.use_default_colors()

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # Selected/current item
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header

        # Get terminal dimensions
        height, width = stdscr.getmaxyx()

        # Find current model position
        current_idx = 0
        for i, model in enumerate(models):
            if model["name"] == app.state.model:
                current_idx = i
                break

        # Set up scrolling variables
        offset = 0
        max_rows = height - 7  # Leave room for header and instructions

        # Main interaction loop
        while True:
            stdscr.clear()

            # Display title and instructions
            stdscr.addstr(0, 0, "Select a model (↑/↓ to navigate, Enter to select, q or Escape to cancel)",
                        curses.A_BOLD)

            # Display models table
            row = 2  # Start after the title

            # Display header
            stdscr.addstr(row, 0, "  Model | Provider | Type | Input Cost | Output Cost | Context",
                        curses.color_pair(2) | curses.A_BOLD)
            row += 1

            # Display separator
            stdscr.addstr(row, 0, "----" + "-" * 20 + "-+-" + "-" * 10 + "-+-" + "-" * 10 +
                        "-+-" + "-" * 12 + "-+-" + "-" * 12 + "-+-" + "-" * 10)
            row += 1

            # Calculate visible range based on current selection
            if current_idx < offset:
                offset = current_idx
            if current_idx >= offset + max_rows:
                offset = current_idx - max_rows + 1

            # Get token dollar value for cost calculations
            price_per_token_scale = Price_Per_Token_Scale()

            # Display visible models
            for i in range(min(max_rows, len(models) - offset)):
                idx = i + offset
                model = models[idx]

                # Extract model data
                model_name = model["name"]
                provider = model["provider"]
                is_think = model["is_think"]
                input_cost = model["input_cost"]
                output_cost = model["output_cost"]
                context_tokens = model["context_tokens"]

                # Format strings
                think_status = "Reasoning" if is_think else "Standard"
                input_cost_str = f"${input_cost*price_per_token_scale:.3f}/M"
                output_cost_str = f"${output_cost*price_per_token_scale:.3f}/M"
                context_str = f"{context_tokens//1024}K"

                # Truncate long model names
                display_name = model_name
                if len(model_name) > 17:
                    display_name = model_name[:14] + "..."

                # Setup formatting
                attr = curses.A_NORMAL
                prefix = "  "

                if idx == current_idx:
                    attr = curses.color_pair(1) | curses.A_BOLD
                    prefix = "→ "
                elif model_name == app.state.model:
                    attr = curses.color_pair(1)
                    prefix = "* "

                # Display the row
                try:
                    model_display = f"{prefix}{display_name:17} | {provider:10} | {think_status:10} | {input_cost_str:12} | {output_cost_str:12} | {context_str:10}"
                    stdscr.addstr(row, 0, model_display[:width-1], attr)
                except curses.error:
                    pass  # Handle overflow safely

                row += 1

            # Display current selection at the bottom
            current_model = models[current_idx]["name"]
            try:
                stdscr.addstr(height-2, 0, f"Current selection: {current_model}",
                            curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

            # Refresh screen
            stdscr.refresh()

            # Handle keypresses
            key = stdscr.getch()

            if key == curses.KEY_UP:
                current_idx = max(0, current_idx - 1)
            elif key == curses.KEY_DOWN:
                current_idx = min(len(models) - 1, current_idx + 1)
            elif key in [ord('\n'), ord('\r'), curses.KEY_ENTER]:
                selected_model = models[current_idx]["name"]
                break
            elif key in [ord('q'), ord('Q'), 27]:  # q, Q, or ESC (27 is the ASCII code for Escape)
                # Exit immediately for both q and Escape
                break
            elif key == curses.KEY_HOME:
                current_idx = 0
            elif key == curses.KEY_END:
                current_idx = len(models) - 1
            elif key == curses.KEY_PPAGE:  # Page Up
                current_idx = max(0, current_idx - max_rows)
            elif key == curses.KEY_NPAGE:  # Page Down
                current_idx = min(len(models) - 1, current_idx + max_rows)

    except Exception:
        # Don't handle exceptions here, let wrapper handle them
        pass

    # No finally block - let the wrapper handle cleanup
    return selected_model
