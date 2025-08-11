import httpx

import logging
logger = logging.getLogger("jrdev")

async def fetch_models_dot_dev(provider_name: str):
    """
    Fetches model data from the OpenRouter API and formats it into the internal model list structure.
    """
    url = "https://models.dev/api.json"
    formatted_models = {}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            api_data = response.json()

        if provider_name not in api_data or "models" not in api_data[provider_name]:
            logger.error(f"No matches in models.dev for {provider_name}")
            return {}

        for model_name, model in api_data[provider_name]["models"].items():
            try:
                input_raw = float(model.get('cost', {}).get('input', '0'))
                output_raw = float(model.get('cost', {}).get('output', '0'))
                # models.dev gives cost per 1m tokens, JrDev stores as cost per 10m
                input_cost = input_raw * 10
                output_cost = output_raw * 10
            except (ValueError, TypeError):
                logger.info(f"Failed to parse model data price:\n {model}")
                input_cost = 0
                output_cost = 0

            formatted_model = {
                "name": model_name,
                "provider": provider_name,
                "is_think": True,  # Defaulting to True - this should be deprecated anyways
                "input_cost": input_cost,
                "output_cost": output_cost,
                "context_tokens": model.get('limit', {}).get('context', 0),
                "release_date": model.get('release_date', "")
            }
            if formatted_model["name"]:
                formatted_models[model_name] = formatted_model

    except httpx.RequestError as e:
        logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
        return {}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return {}

    return formatted_models
