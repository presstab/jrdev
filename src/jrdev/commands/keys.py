"""
Command handler for API key management.
"""
import asyncio
import os
from getpass import getpass
from typing import Dict, Optional, Tuple, Any, Callable
from dotenv import load_dotenv
from functools import partial

from jrdev.file_utils import add_to_gitignore, get_env_path
from jrdev.ui.ui import PrintType


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


async def handle_keys(app: Any, args: list[str]) -> None:
    """Manage API keys through an interactive menu."""
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


async def _view_keys(app: Any) -> None:
    """Display configured API keys (masked for security)."""
    keys = {
        "VENICE_API_KEY": os.getenv("VENICE_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY")
    }
    
    app.ui.print_text("Configured API Keys:", PrintType.INFO)
    for name, value in keys.items():
        if value:
            # Mask the key for security, showing only first 4 and last 4 chars
            if len(value) > 10:
                masked = value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                masked = "*" * len(value)
            app.ui.print_text(f"{name}: {masked} (configured)", PrintType.SUCCESS)
        else:
            app.ui.print_text(f"{name}: Not configured", PrintType.WARNING)
            
    # Wait for user acknowledgment before returning to the main menu
    await async_input("\nPress Enter to continue...")
    app.ui.print_text("Returning to main menu.", PrintType.INFO)


async def _add_update_key(app: Any) -> None:
    """Add or update an API key."""
    services: Dict[str, Tuple[str, str]] = {
        "1": ("VENICE_API_KEY", "Venice AI"),
        "2": ("OPENAI_API_KEY", "OpenAI"),
        "3": ("ANTHROPIC_API_KEY", "Anthropic"),
        "4": ("DEEPSEEK_API_KEY", "DeepSeek"),
        "5": ("", "Cancel/Back")
    }
    
    app.ui.print_text("Select service to add/update key for:", PrintType.INFO)
    for num, (_, name) in services.items():
        app.ui.print_text(f"{num}. {name}", PrintType.INFO)
    
    service_choice = await async_input("Enter your choice (1-5): ")
    
    if service_choice == "5" or service_choice.lower() in ["cancel", "back", "q", "quit", "exit"]:
        app.ui.print_text("Cancelled key update.", PrintType.INFO)
        return
        
    if service_choice not in services:
        app.ui.print_text("Invalid choice.", PrintType.ERROR)
        return
    
    key_name, service_name = services[service_choice]
    is_required = key_name == "VENICE_API_KEY"
    
    app.ui.print_text(f"Enter API key for {service_name} (or press Ctrl+C to cancel):", PrintType.INFO)
    try:
        new_key = await _prompt_key(service_name, required=is_required)
        if new_key:
            keys = _load_current_keys()
            keys[key_name] = new_key
            _save_keys_to_env(keys)
            
            # Reload environment variables
            load_dotenv()
            app.ui.print_text(f"{service_name} API key updated successfully!", PrintType.SUCCESS)
    except KeyboardInterrupt:
        print()  # Add a newline after ^C
        app.ui.print_text("Cancelled key update.", PrintType.INFO)


async def _remove_key(app: Any) -> None:
    """Remove an API key."""
    services: Dict[str, Tuple[str, str]] = {
        "1": ("OPENAI_API_KEY", "OpenAI"),
        "2": ("ANTHROPIC_API_KEY", "Anthropic"),
        "3": ("DEEPSEEK_API_KEY", "DeepSeek"),
        "4": ("", "Cancel/Back")
    }
    
    app.ui.print_text("Select key to remove:", PrintType.INFO)
    for num, (_, name) in services.items():
        app.ui.print_text(f"{num}. {name}", PrintType.INFO)
    
    service_choice = await async_input("Enter your choice (1-4): ")
    
    if service_choice == "4" or service_choice.lower() in ["cancel", "back", "q", "quit", "exit"]:
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
    
    # Cannot remove Venice API key as it's required
    keys = _load_current_keys()
    if key_name in keys:
        del keys[key_name]
        _save_keys_to_env(keys)
        
        # Reload environment variables
        load_dotenv()
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
            app.ui.print_text("This key is required!", PrintType.ERROR)
        except KeyboardInterrupt:
            raise  # Re-raise to allow handling by caller


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


def _save_keys_to_env(keys: Dict[str, str]) -> None:
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


def check_existing_keys() -> bool:
    """
    Check if the required API keys exist in the environment or in the .env file.
    
    Returns:
        True if all required keys exist, False otherwise
    """
    required = ["VENICE_API_KEY"]
    
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
        app.ui.print_text("- Venice AI API key is required", PrintType.WARNING)
        app.ui.print_text("- OpenAI, Anthropic, and DeepSeek keys are optional", PrintType.INFO)
        
        # Instructions
        app.ui.print_text("Security Information:", PrintType.SUBHEADER)
        app.ui.print_text("- API keys will be stored in a local .env file", PrintType.INFO)
        app.ui.print_text("- Restricted file permissions (600) for security", PrintType.INFO)
        app.ui.print_text("- Automatically added to .gitignore", PrintType.INFO)
        
        await async_input("Press Enter to continue with setup...")
        
        # Get the keys
        app.ui.print_text("API Key Configuration", PrintType.HEADER)
        keys = {
            "VENICE_API_KEY": await _prompt_key("Venice AI", required=True),
            "OPENAI_API_KEY": await _prompt_key("OpenAI (optional)"),
            "ANTHROPIC_API_KEY": await _prompt_key("Anthropic (optional)"),
            "DEEPSEEK_API_KEY": await _prompt_key("DeepSeek (optional)")
        }
        
        _save_keys_to_env(keys)
        
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