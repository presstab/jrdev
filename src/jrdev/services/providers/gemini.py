import logging
from typing import Any, Dict, List
from datetime import datetime

import google.genai as genai

from jrdev.services.providers.models_dev import fetch_models_dot_dev

logger = logging.getLogger("jrdev")

async def fetch_gemini_models(core_app: Any) -> List[Dict[str, Any]]:
    """
    Fetches available Gemini models from the Google GenAI API.
    """
    if not genai:
        logger.error("fetch_gemini_models: genai package not available")
        return []

    client = core_app.state.clients.get_client("gemini")
    if not client:
        logger.error("fetch_gemini_models: no client found")
        return []

    models_list = []
    try:
        logger.info("Fetching models from Gemini...")

        # fetch supporting details from models.dev
        model_details = await fetch_models_dot_dev("google")

        response = await client.aio.models.list()
        for model in response:
            if 'generateContent' not in model.supported_actions:
                continue

            model_id = model.name.split('/')[-1]
            is_think = "pro" in model_id.lower()

            formatted_model ={
                "name": model_id,
                "provider": "gemini",
                "is_think": is_think,
                "input_cost": 0,
                "output_cost": 0,
                "context_tokens": model.input_token_limit,
            }

            # add supplemental info from models.dev
            if model_id in model_details:
                formatted_model["input_cost"] = model_details[model_id]["input_cost"]
                formatted_model["output_cost"] = model_details[model_id]["output_cost"]
                formatted_model["context_tokens"] = model_details[model_id]["context_tokens"]

                if "release_date" in model_details[model_id]:
                    release_date = model_details[model_id]["release_date"]
                    if release_date:
                        dt = datetime.strptime(model_details[model_id]["release_date"], "%Y-%m-%d")
                        formatted_model["created"] = dt.timestamp()

            models_list.append(formatted_model)
            
        logger.info(f"Fetched {len(models_list)} models from Gemini.")
        return models_list
    except Exception as e:
        logger.error(f"Failed to fetch models from Gemini: {e}", exc_info=True)
        return []
