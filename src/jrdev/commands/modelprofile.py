import asyncio
import logging
from typing import Any, Dict, List, Optional

from jrdev.models.model_profiles import ModelProfileManager
from jrdev.ui.ui import PrintType, terminal_print

# Get the global logger instance
logger = logging.getLogger("jrdev")


async def async_input(prompt: str = "") -> str:
    """
    Asynchronous version of input() that doesn't block the event loop.

    Args:
        prompt: The prompt to display to the user

    Returns:
        The string entered by the user
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


async def handle_modelprofile(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Manages model profiles, which assign specific models to different task types.

    Profiles allow using a powerful model for complex tasks (e.g., 'advanced_coding')
    and a faster, cheaper model for simpler tasks (e.g., 'quick_reasoning').

    Usage (Interactive):
      /modelprofile - Shows an interactive menu for managing profiles.

    Usage (Non-Interactive):
      /modelprofile list                      - Shows all profiles and their assigned models.
      /modelprofile get <profile_name>        - Shows the model assigned to a specific profile.
      /modelprofile set <profile_name> <model_name> - Sets a profile to use a specific model.
      /modelprofile default <profile_name>    - Sets the default profile for general tasks.
      /modelprofile showdefault               - Shows the current default profile.
    """

    usage_str = """
Usage:
  /modelprofile - Interactive menu for managing profiles
  /modelprofile list - Show all profiles and their assigned models
  /modelprofile get [profile] - Show the model assigned to a profile
  /modelprofile set [profile] [model] - Set a profile to use a specific model
  /modelprofile default [profile] - Set the default profile
  /modelprofile showdefault - Show the current default profile
        """

    manager = app.profile_manager()

    # If no arguments provided, show interactive menu
    if len(args) == 1:
        if app.ui.ui_name == "cli":
            await show_interactive_menu(app, manager)
        else:
            app.ui.print_text(usage_str)
            app.ui.print_text("")
            await list_profiles(app, manager)
        return

    # Process standard command-line arguments
    subcommand = args[1].lower()
    await _handle_subcommand(app, subcommand, args, manager)


def _handle_get(app: Any, args: List[str], manager: Any) -> None:
    # Get model for a specific profile
    if len(args) < 3:
        app.ui.print_text(
            "Missing profile name. Usage: /modelprofile get [profile]",
            PrintType.ERROR,
        )
        return

    profile = args[2]
    model = manager.get_model(profile)
    app.ui.print_text(f"Profile '{profile}' uses model: {model}", PrintType.INFO)


def _handle_set(app: Any, args: List[str], manager: Any) -> None:
    # Set a profile to use a different model
    if len(args) < 4:
        app.ui.print_text(
            "Missing arguments. Usage: /modelprofile set [profile] [model]",
            PrintType.ERROR,
        )
        return

    profile = args[2]
    model = args[3]
    success = manager.update_profile(profile, model, app.state.model_list)

    if not success:
        app.ui.print_text(f"Failed to update profile '{profile}'", PrintType.ERROR)
    else:
        app.ui.print_text(f"Updated {profile} to use model: {model}")


async def _handle_subcommand(app: Any, subcommand: str, args: List[str], manager: Any) -> None:
    """Returns true if handled"""
    if subcommand == "list":
        # List all profiles and their models
        await list_profiles(app, manager)
    elif subcommand == "get":
        _handle_get(app, args, manager)
    elif subcommand == "set":
        _handle_set(app, args, manager)
    elif subcommand == "default":
        # Set the default profile
        if len(args) < 3:
            app.ui.print_text(
                "Missing profile name. Usage: /modelprofile default [profile]",
                PrintType.ERROR,
            )
            return

        profile = args[2]
        success = manager.set_default_profile(profile)

        if success:
            app.ui.print_text(f"Updated {profile} as default profile")
        else:
            app.ui.print_text(f"Failed to set '{profile}' as default profile", PrintType.ERROR)

    elif subcommand == "showdefault":
        # Show the current default profile
        default = manager.get_default_profile()
        model = manager.get_model(default)
        app.ui.print_text(f"Default profile: {default} (using model: {model})", PrintType.INFO)

    else:
        app.ui.print_text(f"Unknown subcommand: {subcommand}", PrintType.ERROR)
        app.ui.print_text(
            "Available subcommands: list, get, set, default, showdefault",
            PrintType.INFO,
        )


async def list_profiles(app: Any, manager: ModelProfileManager) -> None:
    """
    List all available profiles and their assigned models.

    Args:
        manager: The ModelProfileManager instance
    """
    profiles = manager.list_available_profiles()
    default = manager.get_default_profile()

    terminal_print("Available Model Profiles:", PrintType.INFO)
    for profile, model in sorted(profiles.items()):
        if profile == default:
            app.ui.print_text(f"* {profile}: {model} (default)", PrintType.SUCCESS)
        else:
            app.ui.print_text(f"  {profile}: {model}", PrintType.INFO)


async def show_interactive_menu(app: Any, manager: ModelProfileManager) -> None:
    """
    Display an interactive menu for managing model profiles.

    Args:
        app: The Application instance
        manager: The ModelProfileManager instance
    """
    while True:
        # Display current profiles summary at the top
        profiles = manager.list_available_profiles()
        default = manager.get_default_profile()

        terminal_print("Model Profile Management", PrintType.HEADER)
        terminal_print("\nCurrent Profiles:", PrintType.SUBHEADER)

        if profiles:
            # Display all profiles in a nicely formatted way
            for profile, model in sorted(profiles.items()):
                if profile == default:
                    terminal_print(f"* {profile}: {model} (default)", PrintType.SUCCESS)
                else:
                    terminal_print(f"  {profile}: {model}", PrintType.INFO)
        else:
            terminal_print("  No profiles configured", PrintType.WARNING)

        # Then show the menu options
        choices = """
Choose an action:
1. List all profiles
2. Set profile model
3. Set default profile
4. Exit
"""
        terminal_print("\nMenu Options:", PrintType.SUBHEADER)
        terminal_print(choices, PrintType.INFO)

        c = await async_input("Enter your choice (1-4): ")

        if c == "1":
            # List all profiles
            await list_profiles(app, manager)
            await async_input("\nPress Enter to continue...")

        elif c == "2":
            # Set a profile model
            await set_profile_model_interactive(app, manager)

        elif c == "3":
            # Set default profile
            await set_default_profile_interactive(manager)

        elif c == "4" or c.lower() in ["exit", "q", "quit", "cancel"]:
            terminal_print("Exiting profile management.", PrintType.INFO)
            break

        else:
            terminal_print("Invalid choice. Please try again.", PrintType.ERROR)


async def _select_profile(profiles: Dict[str, str], manager: ModelProfileManager) -> int:
    profile_names = sorted(profiles.keys())

    for i, profile in enumerate(profile_names):
        model = profiles[profile]
        is_default = profile == manager.get_default_profile()
        default_tag = " (default)" if is_default else ""
        terminal_print(f"{i+1}. {profile}: {model}{default_tag}", PrintType.INFO)

    terminal_print(f"{len(profile_names)+1}. Cancel", PrintType.INFO)

    # Get user selection
    return int(await async_input(f"Enter your choice (1-{len(profile_names)+1}): "))


async def _select_model(app: Any) -> Optional[Dict[str, Any]]:
    """
    Prints a numbered list of models to the user, then returns
    the chosen model dict, or None if the user cancels or gives an invalid choice.
    """
    # Get available models
    models: List[Dict[str, Any]] = app.get_models()
    providers_dict: Dict[str, List[Dict[str, Any]]] = {}

    for model_info in models:
        if isinstance(model_info, dict) and "name" in model_info and "provider" in model_info:
            provider = str(model_info["provider"])
            if provider not in providers_dict:
                providers_dict[provider] = []
            providers_dict[provider].append(model_info)

    # Display models grouped by provider
    terminal_print("\nAvailable models by provider:", PrintType.INFO)

    # Create a combined list of model details for selection
    all_models: List[Dict[str, Any]] = []

    # Track model index for selection
    model_index = 1

    # Display models by provider with API key status
    for provider in sorted(providers_dict.keys()):
        # Check if user has API key for this provider
        has_api_key = app.state.clients.has_key(provider.lower())

        # Display provider heading
        provider_label = f"{provider}"
        if not has_api_key:
            provider_label += " (no API key)"

        terminal_print(f"\n{provider_label}:", PrintType.SUBHEADER)

        # Display models for this provider
        for model_info in sorted(providers_dict[provider], key=lambda m: m.get("name", "")):
            name = str(model_info.get("name", "unknown"))

            # Store model details for selection
            all_models.append(model_info)

            # Display with appropriate color based on API key status
            if has_api_key:
                terminal_print(f"  {model_index}. {name}", PrintType.INFO)
            else:
                # Display in gray if no API key
                # Use PROCESSING type which includes the DIM color format
                terminal_print(f"  {model_index}. {name} (no API key)", PrintType.PROCESSING)

            model_index += 1

    # Cancel option
    terminal_print(f"\n{model_index}. Cancel", PrintType.INFO)

    # Get user selection
    choice_str = await async_input(f"Enter your choice (1-{model_index}): ")
    try:
        model_choice_num = int(choice_str)
        if 1 <= model_choice_num <= len(all_models):
            return all_models[model_choice_num - 1]
    except ValueError:
        return None

    # cancel or out of range
    return None


async def set_profile_model_interactive(app: Any, manager: ModelProfileManager) -> None:
    """
    Interactive menu for setting a profile's model.

    Args:
        app: The Application instance
        manager: The ModelProfileManager instance
    """
    # Get all profiles
    profiles = manager.list_available_profiles()
    if not profiles:
        terminal_print("No profiles available.", PrintType.ERROR)
        return

    # Display profiles to choose from
    terminal_print("Select a profile to modify:", PrintType.INFO)

    choice_num = await _select_profile(profiles, manager)
    profile_names = sorted(profiles.keys())

    if choice_num == len(profile_names) + 1:
        terminal_print("Cancelled profile selection.", PrintType.INFO)
    elif choice_num < 1 or choice_num > len(profile_names):
        terminal_print("Invalid choice.", PrintType.ERROR)
        return

    selected_profile = profile_names[choice_num - 1]
    current_model = profiles[selected_profile]
    terminal_print(f"Selected profile: {selected_profile}", PrintType.SUCCESS)
    terminal_print(f"Current model: {current_model}", PrintType.INFO)

    selected_model_info = await _select_model(app)
    if selected_model_info is None:
        terminal_print("Cancelled model selection", PrintType.INFO)
        return

    selected_model = str(selected_model_info.get("name", ""))

    # Check if selected model's provider has API key
    provider = str(selected_model_info.get("provider", ""))
    has_api_key = app.state.clients.has_key(provider.lower())

    if not has_api_key:
        terminal_print(
            f"Warning: You don't have an API key for {provider}. This model won't work until " "you add a key.",
            PrintType.WARNING,
        )
        # Ask for confirmation
        confirm = await async_input("Do you still want to set this model? (y/N): ")
        if not confirm.lower().startswith("y"):
            terminal_print("Cancelled model selection.", PrintType.INFO)
            return

    # Pass the terminal's model_list for proper validation
    success = manager.update_profile(selected_profile, selected_model, model_list=app.state.model_list)

    if success:
        terminal_print(
            f"Updated profile '{selected_profile}' to use model '{selected_model}'",
            PrintType.SUCCESS,
        )
    else:
        terminal_print(
            f"Failed to update profile '{selected_profile}'",
            PrintType.ERROR,
        )


async def set_default_profile_interactive(manager: ModelProfileManager) -> None:
    """
    Interactive menu for setting the default profile.

    Args:
        manager: The ModelProfileManager instance
    """
    # Get all profiles
    profiles = manager.list_available_profiles()
    if not profiles:
        terminal_print("No profiles available.", PrintType.ERROR)
        return

    # Display profiles to choose from
    terminal_print("Select a profile to set as default:", PrintType.INFO)
    profile_names = sorted(profiles.keys())
    current_default = manager.get_default_profile()

    for i, profile in enumerate(profile_names):
        model = profiles[profile]
        is_default = profile == current_default
        default_tag = " (current default)" if is_default else ""
        terminal_print(f"{i+1}. {profile}: {model}{default_tag}", PrintType.INFO)

    terminal_print(f"{len(profile_names)+1}. Cancel", PrintType.INFO)

    # Get user selection
    c = await async_input(f"Enter your choice (1-{len(profile_names)+1}): ")

    try:
        choice_num = int(c)
        if 1 <= choice_num <= len(profile_names):
            selected_profile = profile_names[choice_num - 1]

            if selected_profile == current_default:
                terminal_print(
                    f"'{selected_profile}' is already the default profile.",
                    PrintType.INFO,
                )
                return

            success = manager.set_default_profile(selected_profile)

            if success:
                terminal_print(
                    f"Set '{selected_profile}' as the default profile.",
                    PrintType.SUCCESS,
                )
            else:
                terminal_print(
                    f"Failed to set '{selected_profile}' as default profile.",
                    PrintType.ERROR,
                )

        elif choice_num == len(profile_names) + 1:
            terminal_print("Cancelled default profile selection.", PrintType.INFO)
        else:
            terminal_print("Invalid choice.", PrintType.ERROR)
    except ValueError:
        terminal_print("Invalid input. Please enter a number.", PrintType.ERROR)
