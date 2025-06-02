import sys
import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
import anthropic
import json
from pathlib import Path
from jrdev.file_operations.file_utils import get_persistent_storage_path, JRDEV_PACKAGE_DIR
from jrdev.models.api_provider import ApiProvider

# Get the global logger instance
logger = logging.getLogger("jrdev")


class APIClients:
    """Manage API clients for different LLM providers"""

    def __init__(self):
        self._clients: Dict[str, Any] = {}
        self._providers: List[Any] = []
        self._initialized = False
        self._load_provider_config()

    def _load_provider_config(self):
        """Load provider configurations from api_providers.json"""
        user_config_path = get_persistent_storage_path() / "user_api_providers.json"
        if not user_config_path.exists():
            # save defaults to user_config path
            default_config_path = Path(JRDEV_PACKAGE_DIR) / "config" / "api_providers.json"
            try:
                with open(default_config_path, 'r') as f:
                    config = json.load(f)
                    with open(user_config_path, "w") as new_file:
                        json.dump(config, new_file, indent=2)
            except Exception as e:
                logger.error(f"Failed to write new user_api_providers.json to file")
                sys.exit(1)

        try:
            with open(user_config_path, 'r') as f:
                config = json.load(f)
                providers = config.get("providers", [])
                for p in providers:
                    try:
                        provider = ApiProvider.from_dict(p)
                        self._providers.append(provider)
                    except Exception as e:
                        logger.error(f"Failed to import provider {p}")

            # Initialize clients dict with provider names
            self._clients = {provider.name: None for provider in self._providers}
        except Exception as e:
            logger.error(f"Failed to load provider config: {e}")
            sys.exit(1)

    async def initialize(self, env: Dict[str, str]) -> None:
        """Initialize all API clients with environment variables"""
        if self._initialized:
            return

        have_provider = False
        for provider in self._providers:
            env_key = provider.env_key
            api_key = env.get(env_key)
            if api_key:
                have_provider = True
            await self._init_client(provider.name, api_key, provider.base_url)
        if not have_provider:
            # no api keys found, unable to initialize
            logger.info("ApiClients initialize: no api keys found")
            return

        self._initialized = True

    async def _init_client(self, name: str, api_key: Optional[str], base_url: Optional[str]) -> None:
        """Initialize a client based on provider name"""
        if not api_key:
            return

        if name == "anthropic":
            self._clients[name] = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self._clients[name] = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=300)

    def __getattr__(self, name: str):
        """Dynamic property access for clients"""
        if name in self._clients:
            return self._clients[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def provider_list(self):
        """A list of all provider names"""
        return self._providers

    def get_all_clients(self) -> Dict[str, Any]:
        """Get all initialized clients"""
        return {k: v for k, v in self._clients.items() if v is not None}

    def is_initialized(self) -> bool:
        """Check if clients have been initialized"""
        return self._initialized

    def set_dirty(self):
        """Set as not initialized"""
        self._initialized = False

    def set_client_null(self, provider_name):
        self._clients[provider_name] = None