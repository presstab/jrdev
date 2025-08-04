from jrdev.services.providers.open_router import fetch_open_router_models
from jrdev.services.providers.openai import fetch_open_ai_models

from typing import Any


class ModelFetchService:
    async def fetch_provider_models(self, provider_name: str, core_app: Any):
        if provider_name == "open_router":
            return await fetch_open_router_models()
        elif provider_name == "openai":
            return await fetch_open_ai_models(core_app)
        return None