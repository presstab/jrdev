from jrdev.services.providers.open_router import fetch_open_router_models

class ModelFetchService:
    async def fetch_provider_models(self, provider_name: str):
        if provider_name == "open_router":
            return await fetch_open_router_models()
        return None