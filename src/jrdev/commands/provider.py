from typing import Any, List

from jrdev.ui.ui import PrintType
from jrdev.utils.string_utils import is_valid_env_key, is_valid_name, is_valid_url


async def handle_provider(app: Any, args: List[str], _worker_id: str) -> None:
    """
    Manages API provider configurations.

    This allows adding, editing, or removing API providers, which define the
    endpoints and environment keys for different LLM services (e.g., OpenAI,
    Anthropic, or a custom local server).

    Usage:
      /provider <subcommand> [arguments]

    Subcommands:
      list                               - List all configured providers.
      add <name> <env_key> <base_url>    - Add a new provider.
      edit <name> <new_env_key> <new_base_url> - Edit an existing provider.
      remove <name>                      - Remove a provider.
      help                               - Show this usage information.
    """
    if len(args) < 2 or args[1] in ("help", "--help", "-h"):
        app.ui.print_text("API Provider Management", PrintType.HEADER)
        app.ui.print_text("Usage:", PrintType.INFO)
        app.ui.print_text("  /provider list", PrintType.INFO)
        app.ui.print_text("  /provider add <name> <env_key_name> <base_url>", PrintType.INFO)
        app.ui.print_text(
            "    (Adds a new provider. 'required' is set to True, 'default_profiles' is empty.)", PrintType.INFO
        )
        app.ui.print_text("  /provider edit <name> <new_env_key_name> <new_base_url>", PrintType.INFO)
        app.ui.print_text("    (Edits an existing provider's env_key and base_url.)", PrintType.INFO)
        app.ui.print_text("  /provider remove <name>", PrintType.INFO)
        return

    cmd = args[1].lower()

    try:
        if cmd == "list":
            _handle_list(app)
        elif cmd == "add":
            _handle_add(app, args)
        elif cmd == "edit":
            _handle_edit(app, args)
        elif cmd == "remove":
            _handle_remove(app, args)
        else:
            app.ui.print_text(f"Unknown command: {cmd}", PrintType.ERROR)
            app.ui.print_text("Type /provider help for usage.", PrintType.INFO)
    except Exception as e:
        msg = f"Failed to execute provider command: {cmd}. Error: {e}"
        app.ui.print_text(msg)
        app.logger.error(msg)


def _handle_list(app: Any) -> None:
    providers = app.state.clients.list_providers()
    app.ui.print_text("API Providers:", PrintType.INFO)
    for p in providers:
        app.ui.print_text(f"  {p.name} (env_key: {p.env_key}, base_url: {p.base_url})", PrintType.INFO)


def _handle_add(app: Any, args: List[str]) -> None:
    if len(args) < 5:  # /provider add name env_key_name base_url
        app.ui.print_text("Usage: /provider add <name> <env_key_name> <base_url>", PrintType.ERROR)
        return
    name = args[2]
    env_key = args[3]
    base_url = args[4]

    if not is_valid_name(name):
        app.ui.print_text(
            f"Invalid provider name '{name}'. Allowed: 1-64 chars, alphanumeric, underscore, hyphen; no path "
            "separators.",
            PrintType.ERROR,
        )
        return
    if not is_valid_env_key(env_key):
        app.ui.print_text(
            f"Invalid env_key '{env_key}'. Allowed: 1-128 chars, alphanumeric, underscore, hyphen; no path "
            "separators.",
            PrintType.ERROR,
        )
        return
    if not is_valid_url(base_url):
        app.ui.print_text(f"Invalid base_url '{base_url}'. Must be a valid http(s) URL.", PrintType.ERROR)
        return

    provider_data = {
        "name": name,
        "env_key": env_key,
        "base_url": base_url,
        "required": True,
        "default_profiles": {"profiles": {}, "default_profile": ""},
    }
    app.state.clients.add_provider(provider_data)
    app.ui.print_text(f"Provider '{name}' added successfully.", PrintType.SUCCESS)
    app.ui.providers_updated()
    app.refresh_model_list()


def _handle_edit(app: Any, args: List[str]) -> None:
    if len(args) < 5:  # /provider edit name new_env_key_name new_base_url
        app.ui.print_text("Usage: /provider edit <name> <new_env_key_name> <new_base_url>", PrintType.ERROR)
        return
    name = args[2]
    new_env_key = args[3]
    new_base_url = args[4]
    # Input validation (same as 'add')
    if not is_valid_env_key(new_env_key):
        app.ui.print_text(
            f"Invalid env_key '{new_env_key}'. Allowed: 1-128 chars, alphanumeric, underscore, hyphen; no path "
            "separators.",
            PrintType.ERROR,
        )
        return
    if not is_valid_url(new_base_url):
        app.ui.print_text(f"Invalid base_url '{new_base_url}'. Must be a valid http(s) URL.", PrintType.ERROR)
        return
    updated_fields = {"env_key": new_env_key, "base_url": new_base_url}
    app.state.clients.edit_provider(name, updated_fields)
    app.ui.print_text(f"Provider '{name}' edited successfully.", PrintType.SUCCESS)
    app.ui.providers_updated()


def _handle_remove(app: Any, args: List[str]) -> None:
    if len(args) < 3:
        app.ui.print_text("Usage: /provider remove <name>", PrintType.ERROR)
        return
    name = args[2]
    app.state.clients.remove_provider(name)
    app.ui.print_text(f"Provider '{name}' removed successfully.", PrintType.SUCCESS)
    app.ui.providers_updated()
    app.refresh_model_list()
