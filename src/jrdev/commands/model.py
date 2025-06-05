#!/usr/bin/env python3

"""
Model command implementation for the JrDev terminal.
Manages the user's list of available models and the active chat model.
"""
from typing import List
from jrdev.ui.ui import PrintType


def _parse_bool(val: str) -> bool:
    """Parse a string to boolean, accepting common true/false values."""
    true_vals = {"1", "true", "yes", "y", "on"}
    false_vals = {"0", "false", "no", "n", "off"}
    if val.lower() in true_vals:
        return True
    if val.lower() in false_vals:
        return False
    raise ValueError(f"Invalid boolean value: {val}")


async def handle_model(app, args: List[str], worker_id: str):
    """
    Handle the /model command to manage available models and set the active chat model.

    Args:
        app: The Application instance.
        args: Command arguments:
              /model list
              /model set <model_name>
              /model remove <model_name>
              /model add <name> <provider> <is_think> <input_cost> <output_cost> <context_window>
        worker_id: The ID of the worker processing the command (unused in this handler).
    """

    current_chat_model = app.state.model
    available_model_names = app.get_model_names()
    
    detailed_usage_message = (
        "Manages available AI models and the active chat model.\n"
        "Usage:\n"
        "  /model list                       - Shows all models available in your user_models.json.\n"
        "  /model set <model_name>           - Sets the active model for the chat.\n"
        "  /model remove <model_name>        - Removes a model from your user_models.json.\n"
        "  /model add <name> <provider> <is_think> <input_cost> <output_cost> <context_window>\n"
        "      - Add a new model to your user_models.json.\n"
        "        <input_cost> and <output_cost> are the cost per 1,000,000 tokens (as a float, in dollars).\n"
        "        Example: /model add gpt-4 openai true 0.10 0.30 8192\n"
    )

    if len(args) < 2:
        current_chat_model_display = current_chat_model if current_chat_model else "Not set"
        app.ui.print_text(f"Current chat model: {current_chat_model_display}", print_type=PrintType.INFO)
        app.ui.print_text(detailed_usage_message, print_type=PrintType.INFO)
        if available_model_names:
            app.ui.print_text(f"Available models: {', '.join(available_model_names)}", print_type=PrintType.INFO)
        else:
            app.ui.print_text("No models available in your configuration.", PrintType.INFO)
        return

    subcommand = args[1].lower()

    if subcommand == "list":
        if not available_model_names:
            app.ui.print_text("No models available in your user configuration (user_models.json).", PrintType.INFO)
        else:
            app.ui.print_text("Available models (from your user_models.json):", PrintType.INFO)
            for m_name in available_model_names:
                app.ui.print_text(f"  - {m_name}")
        return

    elif subcommand == "set":
        if len(args) < 3:
            app.ui.print_text("Usage: /model set <model_name>", PrintType.ERROR)
            if available_model_names:
                app.ui.print_text(f"Available models: {', '.join(available_model_names)}", PrintType.INFO)
            else:
                app.ui.print_text("No models available to set.", PrintType.INFO)
            return
        
        model_name_to_set = args[2]
        if model_name_to_set in available_model_names:
            app.set_model(model_name_to_set) # This handles persistence of chat_model and UI update
            app.ui.print_text(f"Chat model set to: {model_name_to_set}", print_type=PrintType.SUCCESS)
        else:
            app.ui.print_text(f"Error: Model '{model_name_to_set}' not found in your configuration.", PrintType.ERROR)
            if available_model_names:
                app.ui.print_text(f"Available models: {', '.join(available_model_names)}", PrintType.INFO)
            else:
                app.ui.print_text("No models available in your configuration.", PrintType.INFO)
        return

    elif subcommand == "remove":
        if len(args) < 3:
            app.ui.print_text("Usage: /model remove <model_name>", PrintType.ERROR)
            if available_model_names:
                app.ui.print_text(f"Available models: {', '.join(available_model_names)}", PrintType.INFO)
            else:
                app.ui.print_text("No models available to remove.", PrintType.INFO)
            return

        model_name_to_remove = args[2]
        current_models_full_data = app.get_models() # Fetches List[Dict[str, Any]]

        if not any(m['name'] == model_name_to_remove for m in current_models_full_data):
            app.ui.print_text(f"Error: Model '{model_name_to_remove}' not found in your configuration.", PrintType.ERROR)
            return

        if not app.remove_model(model_name_to_remove):
            app.logger.info(f"Failed to remove model {model_name_to_remove}")
            app.ui.print_text(f"Failed to remove model {model_name_to_remove}")
            return

        app.logger.info(f"Removed model {model_name_to_remove}")
        app.ui.print_text(f"Removed model {model_name_to_remove}")
        return

    elif subcommand == "add":
        # /model add <name> <provider> <is_think> <input_cost> <output_cost> <context_window>
        if len(args) < 8:
            app.ui.print_text(
                "Usage: /model add <name> <provider> <is_think> <input_cost> <output_cost> <context_window>",
                PrintType.ERROR
            )
            app.ui.print_text(
                "Example: /model add gpt-4 openai true 0.10 0.30 8192\n"
                "  <input_cost> and <output_cost> are the cost per 1,000,000 tokens (as a float, in dollars).",
                PrintType.INFO
            )
            return
        name = args[2]
        provider = args[3]
        is_think_str = args[4]
        input_cost_str = args[5]
        output_cost_str = args[6]
        context_window_str = args[7]

        # Validate and parse arguments
        try:
            is_think = _parse_bool(is_think_str)
        except ValueError as e:
            app.ui.print_text(f"Invalid value for is_think: {e}", PrintType.ERROR)
            return
        try:
            input_cost_float = float(input_cost_str)
        except ValueError:
            app.ui.print_text(f"Invalid value for input_cost: '{input_cost_str}' (must be a float)", PrintType.ERROR)
            return
        try:
            output_cost_float = float(output_cost_str)
        except ValueError:
            app.ui.print_text(f"Invalid value for output_cost: '{output_cost_str}' (must be a float)", PrintType.ERROR)
            return
        try:
            context_window = int(context_window_str)
        except ValueError:
            app.ui.print_text(f"Invalid value for context_window: '{context_window_str}' (must be integer)", PrintType.ERROR)
            return

        # Convert costs from per 1,000,000 tokens (float) to per 10,000,000 tokens (int, in dollars)
        input_cost = int(round(input_cost_float * 10))
        output_cost = int(round(output_cost_float * 10))

        # Check for duplicate model name
        if name in available_model_names:
            app.ui.print_text(f"A model named '{name}' already exists in your configuration.", PrintType.ERROR)
            return

        # Add the model
        success = app.add_model(name, provider, is_think, input_cost, output_cost, context_window)
        if success:
            app.logger.info(f"Added model {name} (provider: {provider})")
            app.ui.print_text(f"Successfully added model '{name}' (provider: {provider})", PrintType.SUCCESS)
        else:
            app.logger.info(f"Failed to add model {name} (provider: {provider})")
            app.ui.print_text(f"Failed to add model '{name}' (provider: {provider})", PrintType.ERROR)
        return

    else:
        app.ui.print_text(f"Unknown subcommand: {subcommand}", PrintType.ERROR)
        app.ui.print_text(detailed_usage_message, PrintType.INFO)
