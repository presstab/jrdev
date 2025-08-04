import logging
logger = logging.getLogger("jrdev")

from datetime import timezone
from jrdev.services.providers.models_dev import fetch_models_dot_dev

async def fetch_open_anthropic_models(core_app):
    """
    Fetches model data from the OpenAI API and formats it into the internal model list structure.
    """
    client = core_app.state.clients.get_client("anthropic")
    if not client:
        return []

    # fetch supporting details from models.dev
    model_details = await fetch_models_dot_dev("anthropic")

    try:
        response = await client.models.list(limit=1000)
        models = response.data
    except Exception as e:
        logger.error(f"Failed to fetch Anthropic models: {e}")
        return []

    logger.info(f"Fetched Anthropic models:\n{models}")
    formatted_models = []
    for model in models:
        # convert time created to timestamp
        dt = model.created_at.replace(tzinfo=timezone.utc)

        formatted_model = {
            "name": model.id,
            "provider": "anthropic",
            "is_think": True,
            "input_cost": 0,
            "output_cost": 0,
            "context_tokens": 0,
            "created": int(dt.timestamp()),
        }

        # add supplemental info from models.dev
        if model.id in model_details:
            formatted_model["input_cost"] = model_details[model.id]["input_cost"]
            formatted_model["output_cost"] = model_details[model.id]["output_cost"]
            formatted_model["context_tokens"] = model_details[model.id]["context_tokens"]

        if formatted_model["name"]:
            formatted_models.append(formatted_model)

    return formatted_models
