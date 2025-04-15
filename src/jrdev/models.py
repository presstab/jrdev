import os
from typing import List, Dict, Any
import logging
from jrdev.core.clients import APIClients

logger = logging.getLogger("jrdev")

async def fetch_venice_models(client: Any) -> List[Dict[str, Any]]:
    """Fetch available models from the Venice API."""
    try:
        response = await client.models.list()
        return [
            {
                "name": model.id,
                "provider": "venice",
                "is_think": model.capabilities.get("think", False),
                "context_tokens": model.context_length
            }
            for model in response.data
        ]
    except Exception as e:
        logger.error(f"Error fetching Venice models: {e}")
        return []

async def fetch_models(app: Any) -> List[Dict[str, Any]]:
    """Fetch available models from all configured API providers."""
    models = []
    if hasattr(app.state, 'clients') and app.state.clients.is_initialized():
        for provider in app.state.clients._providers:
            if provider["name"] == "venice" and app.state.clients.venice:
                venice_models = await fetch_venice_models(app.state.clients.venice)
                models.extend(venice_models)
    return models