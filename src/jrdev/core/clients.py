import sys
import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
import anthropic
from jrdev.ui.ui import PrintType

# Get the global logger instance
logger = logging.getLogger("jrdev")


class APIClients:
    """Manage API clients for different LLM providers"""

    def __init__(self):
        self._clients: Dict[str, Any] = {
            "venice": None,
            "openai": None,
            "anthropic": None,
            "deepseek": None
        }
        self._initialized = False

    async def initialize(self, env: Dict[str, str]) -> None:
        """Initialize all API clients with environment variables"""
        if self._initialized:
            return

        await self._init_venice(env.get("VENICE_API_KEY"))
        await self._init_openai(env.get("OPENAI_API_KEY"))
        await self._init_anthropic(env.get("ANTHROPIC_API_KEY"))
        await self._init_deepseek(env.get("DEEPSEEK_API_KEY"))
        self._initialized = True

    async def _init_venice(self, api_key: Optional[str]) -> None:
        """Initialize Venice client (required)"""
        if not api_key:
            logger.error("Error: VENICE_API_KEY not found")
            sys.exit(1)

        self._clients["venice"] = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.venice.ai/api/v1",
        )

    async def _init_openai(self, api_key: Optional[str]) -> None:
        """Initialize OpenAI client (optional)"""
        if api_key:
            self._clients["openai"] = AsyncOpenAI(api_key=api_key)

    async def _init_anthropic(self, api_key: Optional[str]) -> None:
        """Initialize Anthropic client (optional)"""
        if api_key:
            self._clients["anthropic"] = anthropic.AsyncAnthropic(
                api_key=api_key
            )

    async def _init_deepseek(self, api_key: Optional[str]) -> None:
        """Initialize DeepSeek client (optional)"""
        if api_key:
            self._clients["deepseek"] = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
            )

    @property
    def venice(self) -> AsyncOpenAI:
        """Get Venice client"""
        return self._clients["venice"]

    @property
    def openai(self) -> Optional[AsyncOpenAI]:
        """Get OpenAI client"""
        return self._clients["openai"]

    @property
    def anthropic(self) -> Optional[anthropic.AsyncAnthropic]:
        """Get Anthropic client"""
        return self._clients["anthropic"]

    @property
    def deepseek(self) -> Optional[AsyncOpenAI]:
        """Get DeepSeek client"""
        return self._clients["deepseek"]

    def get_all_clients(self) -> Dict[str, Any]:
        """Get all initialized clients"""
        return {k: v for k, v in self._clients.items() if v is not None}

    def is_initialized(self) -> bool:
        """Check if clients have been initialized"""
        return self._initialized
