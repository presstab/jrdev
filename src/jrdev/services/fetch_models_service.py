from jrdev.services.providers.anthropic import fetch_open_anthropic_models
from jrdev.services.providers.generic_openai import fetch_openai_generic_models
from jrdev.services.providers.open_router import fetch_open_router_models
from jrdev.services.providers.gemini import fetch_gemini_models

from typing import Any


class ModelFetchService:
    async def fetch_provider_models(self, provider_name: str, core_app: Any):
        if provider_name == "open_router":
            return await fetch_open_router_models()
        elif provider_name == "anthropic":
            return await fetch_open_anthropic_models(core_app)
        elif provider_name == "gemini":
            return await fetch_gemini_models(core_app)
        else:
            # Attempt using generic open ai format to get models
            return await fetch_openai_generic_models(core_app, provider_name)
