import logging
logger = logging.getLogger("jrdev")

from typing import Any
from jrdev.services.providers.models_dev import fetch_models_dot_dev

async def fetch_openai_generic_models(core_app: Any, provider_name: str):
    """
    Fetches model data from the OpenAI API and formats it into the internal model list structure.
    """
    client = core_app.state.clients.get_client(provider_name)
    if not client:
        return []

    # fetch supporting details from models.dev
    model_details = await fetch_models_dot_dev(provider_name)

    try:
        response = await client.models.list()
        models = response.data
    except Exception as e:
        logger.error(f"Failed to fetch {provider_name} models: {e}")
        return []

    formatted_models = []
    for model in models:
        formatted_model = {
            "name": model.id,
            "provider": provider_name,
            "is_think": True,
            "input_cost": 0,
            "output_cost": 0,
            "context_tokens": 0,
            "created": model.created
        }

        # add supplemental info from models.dev
        if model.id in model_details:
            formatted_model["input_cost"] = model_details[model.id]["input_cost"]
            formatted_model["output_cost"] = model_details[model.id]["output_cost"]
            formatted_model["context_tokens"] = model_details[model.id]["context_tokens"]

        if formatted_model["name"]:
            formatted_models.append(formatted_model)

    return formatted_models
