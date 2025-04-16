"""
Command handler for API key management.
"""
import asyncio
import os
import logging
from getpass import getpass
from typing import Dict, Optional, Tuple, Any, Callable
from dotenv import load_dotenv
from functools import partial

from jrdev.file_utils import add_to_gitignore, get_env_path
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
    else:
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
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        key, value = line.split('=', 1)
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
    with open(env_path, 'w') as f:
        for k, v in filter(lambda x: x[1], keys.items()):
            f.write(f"{k}={v}\n")
    
    # Set restrictive permissions (0o600 = read/write for owner only)
    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass
    
    # Ensure .env is gitignored
    add_to_gitignore(".gitignore", ".env", create_if_dne=True)


def check_existing_keys(app: Any) -> bool:
    """
    Check if the required API keys exist in the environment or in the .env file.
    
    Returns:
        True if all required keys exist, False otherwise
    """
    required = [provider["env_key"] for provider in app.state.clients._providers if provider["required"]]
    
    # First check if keys are already in environment
    if all(os.getenv(key) for key in required):
        return True
    
    # If not in environment, check if they exist in .env file
    env_path = get_env_path()
    if not os.path.exists(env_path):
        return False
        
    # Parse .env file to check for required keys
    keys = _load_current_keys()
    return all(key in keys and keys[key] for key in required)


async def handle_keys(app: Any, args: list[str], worker_id: str) -> None:
    """Manage API keys through a menu or non-interactive commands."""
    # If UI is textual, handle non-interactively
    if app.ui.ui_name == "textual":
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
            for provider in app.state.clients._providers:
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
    else:
        app.ui.print_text("Invalid choice. Please try again.", PrintType.ERROR)


async def _view_keys(app: Any, textual_mode: bool = False) -> None:
    """Display configured API keys (masked for security)."""
    # Always reload the current keys from the .env file to reflect actual state
    keys = _load_current_keys()
    app.ui.print_text("Configured API Keys:", PrintType.INFO)
    for provider in app.state.clients._providers:
        key_name = provider["env_key"]
        service_name = provider["name"].title()
        value = keys.get(key_name)
        if value:
            masked = _mask_key(value)
            app.ui.print_text(f"{key_name}: {masked} (configured)", PrintType.SUCCESS)
        else:
            app.ui.print_text(f"{key_name}: Not configured", PrintType.WARNING)
    if not textual_mode:
        await async_input("\nPress Enter to continue...")
        app.ui.print_text("Returning to main menu.", PrintType.INFO)


async def _add_update_key(app: Any, service: Optional[str] = None, api_key: Optional[str] = None, textual_mode: bool = False) -> None:
    """Add or update an API key."""
    if textual_mode:
        # service is the name or env_key, api_key is the value
        # Find provider by name or env_key
        provider = None
        for p in app.state.clients._providers:
            if service.lower() == p["name"].lower() or service.upper() == p["env_key"]:
                provider = p
                break
        if not provider:
            app.ui.print_text(f"Unknown service: {service}", PrintType.ERROR)
            return
        key_name = provider["env_key"]
        is_required = provider["required"]
        if not api_key and is_required:
            app.ui.print_text(f"API key for {provider['name']} is required.", PrintType.ERROR)
            return
        keys = _load_current_keys()
        keys[key_name] = api_key
        save_keys_to_env(keys)
        load_dotenv()
        app.ui.print_text(f"{provider['name'].title()} API key updated successfully!", PrintType.SUCCESS)
        return

    # Interactive mode
    services = {}
    for i, provider in enumerate(app.state.clients._providers, 1):
        services[str(i)] = (provider["env_key"], provider["name"].title())
    services[str(len(services) + 1)] = ("", "Cancel/Back")
    
    app.ui.print_text("Select service to add/update key for:", PrintType.INFO)
    for num, (_, name) in services.items():
        app.ui.print_text(f"{num}. {name}", PrintType.INFO)
    
    service_choice = await async_input("Enter your choice (1-{}): ".format(len(services)))
    
    if service_choice == str(len(services)) or service_choice.lower() in ["cancel", "back", "q", "quit", "exit"]:
        app.ui.print_text("Cancelled key update.", PrintType.INFO)
        return
        
    if service_choice not in services:
        app.ui.print_text("Invalid choice.", PrintType.ERROR)
        return
    
    key_name, service_name = services[service_choice]
    is_required = any(provider["env_key"] == key_name and provider["required"] for provider in app.state.clients._providers)
    
    app.ui.print_text(f"Enter API key for {service_name} (or press Ctrl+C to cancel):", PrintType.INFO)
    try:
        new_key = await _prompt_key(service_name, required=is_required)
        if new_key:
            keys = _load_current_keys()
            keys[key_name] = new_key
            save_keys_to_env(keys)
            
            # Reload environment variables
            load_dotenv()
            app.ui.print_text(f"{service_name} API key updated successfully!", PrintType.SUCCESS)
    except KeyboardInterrupt:
        print()  # Add a newline after ^C
        app.ui.print_text("Cancelled key update.", PrintType.INFO)


async def _remove_key(app: Any, service: Optional[str] = None, textual_mode: bool = False) -> None:
    """Remove an API key."""
    if textual_mode:
        # service is the name or env_key
        provider = None
        for p in app.state.clients._providers:
            if service.lower() == p["name"].lower() or service.upper() == p["env_key"]:
                provider = p
                break
        if not provider:
            app.ui.print_text(f"Unknown service: {service}", PrintType.ERROR)
            return
        if provider["required"]:
            app.ui.print_text(f"Cannot remove required key: {provider['name']}", PrintType.ERROR)
            return
        key_name = provider["env_key"]
        keys = _load_current_keys()
        if key_name in keys:
            del keys[key_name]
            save_keys_to_env(keys)
            try:
                del os.environ[key_name]
            except KeyError:
                logger.info(f"_remove_key(): No env var: {key_name}")

            await app.reload_api_clients()
            load_dotenv(get_env_path(), override=True)
            app.ui.print_text(f"{provider['name'].title()} API key removed successfully!", PrintType.SUCCESS)
        else:
            app.ui.print_text(f"{provider['name'].title()} API key not found.", PrintType.WARNING)
        return

    # Interactive mode
    services = {}
    for i, provider in enumerate([p for p in app.state.clients._providers if not p["required"]], 1):
        services[str(i)] = (provider["env_key"], provider["name"].title())
    services[str(len(services) + 1)] = ("", "Cancel/Back")
    
    app.ui.print_text("Select key to remove:", PrintType.INFO)
    for num, (_, name) in services.items():
        app.ui.print_text(f"{num}. {name}", PrintType.INFO)
    
    service_choice = await async_input("Enter your choice (1-{}): ".format(len(services)))
    
    if service_choice == str(len(services)) or service_choice.lower() in ["cancel", "back", "q", "quit", "exit"]:
        app.ui.print_text("Cancelled key removal.", PrintType.INFO)
        return
        
    if service_choice not in services:
        app.ui.print_text("Invalid choice.", PrintType.ERROR)
        return
    
    key_name, service_name = services[service_choice]
    
    # Confirm removal
    confirm = await async_input(f"Are you sure you want to remove the {service_name} API key? (y/n): ")
    if confirm.lower() not in ["y", "yes"]:
        app.ui.print_text("Key removal cancelled.", PrintType.INFO)
        return
    
    keys = _load_current_keys()
    if key_name in keys:
        del keys[key_name]
        save_keys_to_env(keys)
        
        # Reload environment variables
        load_dotenv(get_env_path(), override=True)
        app.ui.print_text(f"{service_name} API key removed successfully!", PrintType.SUCCESS)
    else:
        app.ui.print_text(f"{service_name} API key not found.", PrintType.WARNING)


async def _prompt_key(service: str, required: bool = False) -> str:
    """
    Prompt the user for an API key with masking.
    
    Args:
        service: The service name to display in the prompt
        required: Whether the key is required or optional
        
    Returns:
        The API key entered by the user, or an empty string if skipped
        
    Raises:
        KeyboardInterrupt: If the user presses Ctrl+C to cancel
    """
    while True:
        try:
            prompt = f"{service} API key"
            if required:
                prompt += " (required)"
            else:
                prompt += " (press Enter to skip)"
            prompt += ": "
                
            value = await async_getpass(prompt)
            if value or not required:
                return value
            # If required and empty, print error
            print("This key is required!")
        except KeyboardInterrupt:
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
        
        app.ui.print_text("This appears to be your first time running JrDev.", PrintType.INFO)
        app.ui.print_text("Let's set up your API keys to get started.", PrintType.INFO)
        
        app.ui.print_text("API Key Requirements:", PrintType.SUBHEADER)
        for provider in app.state.clients._providers:
            if provider["required"]:
                app.ui.print_text(f"- {provider['name'].title()} API key is required", PrintType.WARNING)
            else:
                app.ui.print_text(f"- {provider['name'].title()} key is optional", PrintType.INFO)
        
        # Instructions
        app.ui.print_text("Security Information:", PrintType.SUBHEADER)
        app.ui.print_text("- API keys will be stored in a local .env file", PrintType.INFO)
        app.ui.print_text("- Restricted file permissions (600) for security", PrintType.INFO)
        app.ui.print_text("- Automatically added to .gitignore", PrintType.INFO)

        await async_input("Press Enter to continue with setup...")

        # Get the keys
        app.ui.print_text("API Key Configuration", PrintType.HEADER)
        keys = {}
        for provider in app.state.clients._providers:
            keys[provider["env_key"]] = await _prompt_key(f"{provider['name'].title()} {'(optional)' if not provider['required'] else ''}", required=provider["required"])
        
        save_keys_to_env(keys)
        
        # Reload environment variables
        load_dotenv()
        
        # Success message
        app.ui.print_text("Setup complete!", PrintType.SUCCESS)
        app.ui.print_text("Your API keys have been saved securely.", PrintType.INFO)
        app.ui.print_text("You can manage your keys anytime with the /keys command.", PrintType.INFO)
        
        return True
    except KeyboardInterrupt:
        app.ui.print_text("Setup cancelled.", PrintType.WARNING)
        app.ui.print_text("You can run setup again with the /keys command.", PrintType.INFO)
        return False
    except Exception as e:
        app.ui.print_text(f"Error during setup: {str(e)}", PrintType.ERROR)
        app.ui.print_text("You can try again with the /keys command.", PrintType.INFO)
        return False