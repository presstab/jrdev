"""
Command handler for API key management.
"""

import asyncio
import logging
import os
from getpass import getpass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from jrdev.file_operations.file_utils import add_to_gitignore, get_env_path
from jrdev.models.api_provider import ApiProvider
from jrdev.ui.ui import PrintType

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


async def async_getpass(prompt: str = "") -> str:
    """
    Asynchronous version of getpass() that doesn't block the event loop.

    Args:
        prompt: The prompt to display to the user

    Returns:
        The password entered by the user
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: getpass(prompt))


def _mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) > 10:
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
    return "*" * len(value)


def _load_current_keys() -> Dict[str, str]:
    """
    Load current keys from the .env file.

    Returns:
        Dictionary of current API keys
    """
    keys: Dict[str, str] = {}
    env_path = get_env_path()

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        key, value = line.split("=", 1)
                        keys[key] = value
                    except ValueError:
                        # Skip malformed lines
                        continue

    return keys


def save_keys_to_env(keys: Dict[str, str]) -> None:
    """
    Save API keys to .env file with proper permissions.

    Args:
        keys: Dictionary of API keys to save
    """
    env_path = get_env_path()

    # Filter out empty values and write to file
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in filter(lambda x: x[1], keys.items()):
            f.write(f"{k}={v}\n")
            os.environ[k] = v

    # Set restrictive permissions (0o600 = read/write for owner only)
    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass

    # Ensure .env is gitignored
    add_to_gitignore(".gitignore", ".env", create_if_dne=True)


def check_existing_keys(app: Any) -> bool:
    """
    Check if at least one API key exists in the environment or in the .env file.

    Returns:
        True if at least one API key exists, False otherwise
    """
    # 1. Identify All Possible Keys
    all_possible_env_keys = [provider.env_key for provider in app.state.clients.provider_list()]

    # 2. Check Environment Variables
    for key_name in all_possible_env_keys:
        if os.getenv(key_name):
            return True  # Found at least one key in environment

    # 3. Check the .env File
    env_path = get_env_path()
    if not os.path.exists(env_path):
        return False  # .env file doesn't exist, so no keys there

    keys_from_env_file = _load_current_keys()
    for key_name in all_possible_env_keys:
        if key_name in keys_from_env_file and keys_from_env_file[key_name]:
            return True  # Found at least one key in .env file

    # 4. No Keys Found
    return False


def _find_provider_by_service(app: Any, service: str) -> Optional[Dict[str, Any]]:
    """
    Find a provider by service name or environment key.

    Args:
        app: The application instance
        service: Service name or environment key to search for

    Returns:
        Provider dictionary if found, None otherwise
    """
    for provider in app.state.clients.provider_list():
        if service.lower() == provider.name.lower() or service.upper() == provider.env_key:
            return provider
    return None


def _can_remove_key(app: Any, key_name_to_remove: str) -> bool:
    """
    Check if a key can be removed without violating the 'at least one key' rule.

    Args:
        app: The application instance
        key_name_to_remove: The environment key name to check for removal

    Returns:
        True if the key can be safely removed, False otherwise
    """
    keys_before_removal = _load_current_keys()
    temp_keys_after_removal = keys_before_removal.copy()
    if key_name_to_remove in temp_keys_after_removal:
        del temp_keys_after_removal[key_name_to_remove]

    # Check if any other key exists in environment or remaining .env keys
    other_key_exists = False
    for provider in app.state.clients.provider_list():
        pk = provider["env_key"]
        if pk == key_name_to_remove:
            continue  # Skip the one we are trying to remove
        if os.getenv(pk) or (pk in temp_keys_after_removal and temp_keys_after_removal[pk]):
            other_key_exists = True
            break

    if not other_key_exists and not os.getenv(key_name_to_remove):
        # Check if the key to remove is the *only* key in the .env file
        is_only_key_in_env_file = True
        for k, v in keys_before_removal.items():
            if k != key_name_to_remove and v:
                is_only_key_in_env_file = False
                break
        if (
            is_only_key_in_env_file
            and key_name_to_remove in keys_before_removal
            and keys_before_removal[key_name_to_remove]
        ):
            return False

    return True


async def _perform_key_removal(app: Any, key_name_to_remove: str, provider_name: str) -> bool:
    """
    Perform the actual key removal operations.

    Args:
        app: The application instance
        key_name_to_remove: The environment key name to remove
        provider_name: The provider name for the key

    Returns:
        True if the key was found and removed, False if not found
    """
    keys = _load_current_keys()
    if key_name_to_remove in keys:
        del keys[key_name_to_remove]
        save_keys_to_env(keys)
        try:
            del os.environ[key_name_to_remove]
        except KeyError:
            logger.info("_perform_key_removal(): No env var: %s", key_name_to_remove)

        app.state.clients.set_client_null(provider_name)
        await app.reload_api_clients()
        load_dotenv(get_env_path(), override=True)
        return True
    return False


def _validate_key_removal(app: Any, service: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], bool]:
    """
    Validate if a key can be removed by checking provider existence and 'at least one key' rule.

    Args:
        app: The application instance
        service: Service name or environment key to validate for removal

    Returns:
        Tuple of (provider_dict, error_message, can_remove)
        - provider_dict: The provider dictionary if found, None otherwise
        - error_message: Error message if validation fails, None if successful
        - can_remove: True if the key can be safely removed, False otherwise
    """
    # Find provider by name or env_key
    provider_to_remove = _find_provider_by_service(app, service)
    if not provider_to_remove:
        return None, f"Unknown service: {service}", False

    key_name_to_remove = provider_to_remove["env_key"]

    # Check if removing this key would violate the 'at least one key' rule
    if not _can_remove_key(app, key_name_to_remove):
        return (
            provider_to_remove,
            f"Cannot remove {provider_to_remove['name']}: At least one API key must be configured.",
            False,
        )

    return provider_to_remove, None, True


async def _execute_key_removal(app: Any, provider: Dict[str, Any]) -> None:
    """
    Execute the key removal workflow.

    Args:
        app: The application instance
        provider: The provider dictionary for the key to remove

    Returns:
        Tuple of (success, message)
        - success: True if the key was found and removed, False if not found
        - message: Success or warning message about the removal result
    """
    key_name_to_remove = provider["env_key"]
    provider_name = provider["name"]

    if await _perform_key_removal(app, key_name_to_remove, provider_name):
        app.ui.print_text(f"{provider_name.title()} API key removed successfully!", PrintType.SUCCESS)
    else:
        app.ui.print_text(f"{provider_name.title()} API key not found.", PrintType.WARNING)


async def _handle_keys_non_interactive(app: Any, args: list[str]) -> None:
    # Always show help if no subcommand or help flags
    if len(args) < 2 or (len(args) > 1 and args[1] in ("help", "--help", "-h")):
        app.ui.print_text("API Key Management (textual mode)", PrintType.HEADER)
        app.ui.print_text("Usage:", PrintType.INFO)
        app.ui.print_text("  /keys view", PrintType.INFO)
        app.ui.print_text("  /keys add <SERVICE> <API_KEY>", PrintType.INFO)
        app.ui.print_text("  /keys update <SERVICE> <API_KEY>", PrintType.INFO)
        app.ui.print_text("  /keys remove <SERVICE>", PrintType.INFO)
        app.ui.print_text("  /keys list", PrintType.INFO)
        app.ui.print_text("  /keys help", PrintType.INFO)
        app.ui.print_text("Available services:", PrintType.INFO)
        for provider in app.state.clients.provider_list():
            app.ui.print_text(f"  {provider['name'].lower()} ({provider['env_key']})", PrintType.INFO)
        return
    cmd = args[1].lower()
    if cmd in ("view", "list"):
        await _view_keys(app, textual_mode=True)
    elif cmd in ("add", "update"):
        if len(args) < 4:
            app.ui.print_text("Usage: /keys add <SERVICE> <API_KEY>", PrintType.ERROR)
            return
        service = args[2]
        api_key = args[3]
        await _add_update_key(app, service, api_key, textual_mode=True)
    elif cmd == "remove":
        if len(args) < 3:
            app.ui.print_text("Usage: /keys remove <SERVICE>", PrintType.ERROR)
            return
        service = args[2]
        await _remove_key(app, service, textual_mode=True)
    else:
        app.ui.print_text(f"Unknown command: {cmd}", PrintType.ERROR)
        app.ui.print_text("Type /keys help for usage.", PrintType.INFO)
    return


async def _handle_keys_interactive(app: Any) -> None:
    # Interactive (non-textual) mode
    choices = """
        1. View configured keys
        2. Add/Update key
        3. Remove key
        4. Cancel/Exit
        """

    app.ui.print_text("API Key Management", PrintType.HEADER)
    app.ui.print_text(choices, PrintType.INFO)

    choice = await async_input("Enter your choice (1-4): ")

    if choice == "1":
        await _view_keys(app)
    elif choice == "2":
        await _add_update_key(app)
    elif choice == "3":
        await _remove_key(app)
    elif choice == "4" or choice.lower() in ["cancel", "exit", "q", "quit"]:
        app.ui.print_text("Cancelled API key management.", PrintType.INFO)
        return

    app.ui.print_text("Invalid choice. Please try again.", PrintType.ERROR)


async def handle_keys(app: Any, args: list[str], _worker_id: str) -> None:
    """Router:Ignore Manage API keys through a menu or non-interactive commands."""
    # If UI is textual, handle non-interactively
    if app.ui.ui_name == "textual":
        await _handle_keys_non_interactive(app, args)
        return

    await _handle_keys_interactive(app)


async def _view_keys(app: Any, textual_mode: bool = False) -> None:
    """Display configured API keys (masked for security)."""
    # Always reload the current keys from the .env file to reflect actual state
    keys = _load_current_keys()
    app.ui.print_text("Configured API Keys:", PrintType.INFO)
    for provider in app.state.clients.provider_list():
        key_name = provider["env_key"]
        value = keys.get(key_name)
        if value:
            masked = _mask_key(value)
            app.ui.print_text(f"{key_name}: {masked} (configured)", PrintType.SUCCESS)
        else:
            app.ui.print_text(f"{key_name}: Not configured", PrintType.WARNING)
    if not textual_mode:
        await async_input("\nPress Enter to continue...")
        app.ui.print_text("Returning to main menu.", PrintType.INFO)


def _add_update_non_interactive(app: Any, service: str, api_key: str, provider_list: List[ApiProvider]) -> None:
    # service is the name or env_key, api_key is the value
    # Find provider by name or env_key
    provider = None
    for p in provider_list:
        if service.lower() == p.name.lower() or service.upper() == p.env_key:
            provider = p
            break
    if not provider:
        app.ui.print_text(f"Unknown service: {service}", PrintType.ERROR)
        return
    key_name = provider.env_key
    is_required = provider.required

    if not api_key and is_required:  # This check might be re-evaluated based on overall app logic for adding keys.
        app.ui.print_text(f"API key for {provider.name} is required by its configuration.", PrintType.ERROR)
        return

    keys = _load_current_keys()
    keys[key_name] = api_key
    save_keys_to_env(keys)
    load_dotenv()
    app.ui.print_text(f"{provider.name.title()} API key updated successfully!", PrintType.SUCCESS)


async def _add_update_key_interactive(app: Any, provider_list: List[ApiProvider]) -> None:
    # Interactive mode
    services = {}
    for i, provider in enumerate(provider_list, 1):
        services[str(i)] = (provider.env_key, provider.name.title())
    services[str(len(services) + 1)] = ("", "Cancel/Back")

    app.ui.print_text("Select service to add/update key for:", PrintType.INFO)
    for num, (_, name) in services.items():
        app.ui.print_text(f"{num}. {name}", PrintType.INFO)

    service_choice = await async_input(f"Enter your choice (1-{len(services)}): ")

    if service_choice == str(len(services)) or service_choice.lower() in ["cancel", "back", "q", "quit", "exit"]:
        app.ui.print_text("Cancelled key update.", PrintType.INFO)
        return

    if service_choice not in services:
        app.ui.print_text("Invalid choice.", PrintType.ERROR)
        return

    key_name, service_name = services[service_choice]
    # The 'required' flag here is for the _prompt_key function's behavior, not for overall app validation.
    is_required_by_provider_config = any(
        provider.env_key == key_name and provider.required for provider in provider_list
    )

    app.ui.print_text(f"Enter API key for {service_name} (or press Ctrl+C to cancel):", PrintType.INFO)
    try:
        new_key = await _prompt_key(service_name, required=is_required_by_provider_config)
        if new_key is not None:  # Allow empty string if not required by provider config
            keys = _load_current_keys()
            keys[key_name] = new_key
            save_keys_to_env(keys)

            # Reload environment variables
            load_dotenv()
            app.ui.print_text(f"{service_name} API key updated successfully!", PrintType.SUCCESS)
    except KeyboardInterrupt:
        print()  # Add a newline after ^C
        app.ui.print_text("Cancelled key update.", PrintType.INFO)


async def _add_update_key(app: Any, service: str = "", api_key: str = "", textual_mode: bool = False) -> None:
    """Add or update an API key."""
    provider_list = app.state.clients.provider_list()
    if textual_mode:
        _add_update_non_interactive(app, service, api_key, provider_list)
        return

    await _add_update_key_interactive(app, provider_list)


async def _remove_key_non_interactive(app: Any, service: str = "") -> None:
    # Validate the removal request
    provider_to_remove, error_message, can_remove = _validate_key_removal(app, service)
    if not can_remove or not provider_to_remove:
        app.logger.error(f"_remove_key: {error_message}")
        app.ui.print_text(error_message, PrintType.ERROR)
        return

    # Execute the removal
    await _execute_key_removal(app, provider_to_remove)


async def _remove_key_interactive(app: Any) -> None:
    # Filter list to show only configured keys for removal
    keys = _load_current_keys()
    removable_services = {}
    idx = 1
    for provider in app.state.clients.provider_list():
        if provider["env_key"] in keys and keys[provider["env_key"]]:
            removable_services[str(idx)] = (provider["env_key"], provider["name"].title(), provider)
            idx += 1
    removable_services[str(idx)] = ("", "Cancel/Back", None)

    if len(removable_services) == 1:  # Only Cancel/Back
        app.ui.print_text("No configured API keys to remove.", PrintType.INFO)
        return

    app.ui.print_text("Select key to remove:", PrintType.INFO)
    for num, (_, name, _) in removable_services.items():
        app.ui.print_text(f"{num}. {name}", PrintType.INFO)

    service_choice = await async_input(f"Enter your choice (1-{len(removable_services)}): ")

    if service_choice == str(len(removable_services)) or service_choice.lower() in [
        "cancel",
        "back",
        "q",
        "quit",
        "exit",
    ]:
        app.ui.print_text("Cancelled key removal.", PrintType.INFO)
        return

    if service_choice not in removable_services:
        app.ui.print_text("Invalid choice.", PrintType.ERROR)
        return

    _, service_name, provider_to_remove = removable_services[service_choice]

    # Validate the removal using the shared validation function
    _, error_message, can_remove = _validate_key_removal(app, provider_to_remove["name"])
    if not can_remove:
        app.ui.print_text(error_message, PrintType.ERROR)
        return

    # Confirm removal
    confirm = await async_input(f"Are you sure you want to remove the {service_name} API key? (y/n): ")
    if confirm.lower() not in ["y", "yes"]:
        app.ui.print_text("Key removal cancelled.", PrintType.INFO)
        return

    # Execute the removal using the shared execution function
    await _execute_key_removal(app, provider_to_remove)


async def _remove_key(app: Any, service: str = "", textual_mode: bool = False) -> None:
    """Remove an API key."""
    if textual_mode:
        await _remove_key_non_interactive(app, service)
        return

    # Interactive mode
    await _remove_key_interactive(app)


async def _prompt_key(service: str, required: bool = False) -> Optional[str]:
    """
    Prompt the user for an API key with masking.

    Args:
        service: The service name to display in the prompt
        required: Whether the key is considered required by its provider configuration (for prompt text)

    Returns:
        The API key entered by the user, or an empty string if skipped (and not required), or None if cancelled.

    Raises:
        KeyboardInterrupt: If the user presses Ctrl+C to cancel
    """
    while True:
        try:
            prompt = f"{service} API key"
            if required:
                prompt += " (required by provider config)"
            else:
                prompt += " (press Enter to skip/leave empty)"
            prompt += ": "

            value = await async_getpass(prompt)
            if value or not required:
                return value
            # If required by provider config and empty, print error and re-prompt
            print(
                "This key is marked as required by its provider configuration. Please enter a value or Ctrl+C to "
                "cancel."
            )
        except KeyboardInterrupt:
            logger.info("_prompt_key: KeyboardInterrupt")
            raise  # Re-raise to allow handling by caller


async def run_first_time_setup(app: Any) -> bool:
    """
    Run first-time setup to configure API keys.

    Returns:
        True if setup was completed successfully, False otherwise
    """
    try:
        # Welcome message
        app.ui.print_text("Welcome to JrDev!", PrintType.HEADER)

        app.ui.print_text(
            "This appears to be your first time running JrDev, or no API keys are configured.", PrintType.INFO
        )
        app.ui.print_text("Let's set up your API keys to get started.", PrintType.INFO)
        app.ui.print_text("JrDev requires at least one API key to be configured to function.", PrintType.WARNING)

        app.ui.print_text("Available API Providers:", PrintType.SUBHEADER)
        provider_list = app.state.clients.provider_list()
        for provider in provider_list:
            # The 'required' flag from provider config is less relevant now for the overall setup,
            # but can be mentioned for user info.
            req_text = "(provider suggests this key for full functionality)" if provider["required"] else "(optional)"
            app.ui.print_text(f"- {provider['name'].title()} {req_text}", PrintType.INFO)

        # Instructions
        app.ui.print_text("Security Information:", PrintType.SUBHEADER)
        app.ui.print_text("- API keys will be stored in a local .env file", PrintType.INFO)
        app.ui.print_text("- Restricted file permissions (600) for security", PrintType.INFO)
        app.ui.print_text("- Automatically added to .gitignore", PrintType.INFO)

        await async_input("Press Enter to continue with setup...")

        # Get the keys
        app.ui.print_text("API Key Configuration", PrintType.HEADER)
        keys_entered = {}
        num_keys_provided = 0
        for provider in provider_list:
            # Pass the provider's 'required' flag to _prompt_key for its prompt text only.
            # The actual enforcement is 'at least one key overall'.
            key_value = await _prompt_key(f"{provider['name'].title()}", required=provider["required"])
            if key_value:
                keys_entered[provider["env_key"]] = key_value
                num_keys_provided += 1
            elif key_value == "":  # Explicitly skipped (empty string)
                keys_entered[provider["env_key"]] = ""  # Store empty if user explicitly skipped

        if num_keys_provided == 0:
            app.ui.print_text("No API keys were provided. JrDev requires at least one key.", PrintType.ERROR)
            app.ui.print_text("Please run '/keys' to add an API key.", PrintType.INFO)
            # Save whatever was entered (even if all empty, to create .env if needed)
            save_keys_to_env(keys_entered)
            return False

        save_keys_to_env(keys_entered)

        # Reload environment variables
        load_dotenv()

        # Success message
        app.ui.print_text("Setup complete!", PrintType.SUCCESS)
        app.ui.print_text("Your API keys have been saved securely.", PrintType.INFO)
        app.ui.print_text("You can manage your keys anytime with the /keys command.", PrintType.INFO)

        return True
    except KeyboardInterrupt:
        print()  # Newline after ^C
        app.ui.print_text("Setup cancelled.", PrintType.WARNING)
        app.ui.print_text("JrDev requires at least one API key. You can run '/keys' to add one later.", PrintType.INFO)
        return False
    except Exception as e:
        app.ui.print_text(f"Error during setup: {str(e)}", PrintType.ERROR)
        app.ui.print_text("You can try again with the /keys command.", PrintType.INFO)
        return False
