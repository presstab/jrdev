import sys
import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
import anthropic
import json
from pathlib import Path
from jrdev.ui.ui import PrintType

# Get the global logger instance
logger = logging.getLogger("jrdev")


class APIClients:
    """Manage API clients for different LLM providers"""

    def __init__(self):
        self._clients: Dict[str, Any] = {}
        self._initialized = False
        self._load_provider_config()

    def _load_provider_config(self):
        """Load provider configurations from api_providers.json"""
        config_path = Path(__file__).parent.parent / "config" / "api_providers.json"
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self._providers = config.get("providers", [])
            # Initialize clients dict with provider names
            self._clients = {provider["name"]: None for provider in self._providers}
        except Exception as e:
            logger.error(f"Failed to load provider config: {e}")
            sys.exit(1)

    async def initialize(self, env: Dict[str, str]) -> None:
        """Initialize all API clients with environment variables"""
        if self._initialized:
            return

        for provider in self._providers:
            env_key = provider["env_key"]
            api_key = env.get(env_key)
            if provider["required"] and not api_key:
                logger.error(f"Error: {env_key} not found")
                sys.exit(1)
            await self._init_client(provider["name"], api_key, provider["base_url"])
        self._initialized = True

    async def _init_client(self, name: str, api_key: Optional[str], base_url: Optional[str]) -> None:
        """Initialize a client based on provider name"""
        if not api_key:
            return

        if name == "anthropic":
            self._clients[name] = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self._clients[name] = AsyncOpenAI(api_key=api_key, base_url=base_url)

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