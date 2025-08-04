import httpx

import logging
logger = logging.getLogger("jrdev")

async def fetch_open_router_models():
    """
    Fetches model data from the OpenRouter API and formats it into the internal model list structure.
    """
    url = "https://openrouter.ai/api/v1/models"
    formatted_models = []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            api_data = response.json()

        for model in api_data.get('data', []):
            try:
                input_raw = float(model.get('pricing', {}).get('prompt', '0'))
                output_raw = float(model.get('pricing', {}).get('completion', '0'))
                # open router gives pricing per token, we store pricing per 10,000,000 tokens
                input_cost = input_raw * float(10_000_000)
                output_cost = output_raw * float(10_000_000)
            except (ValueError, TypeError):
                logger.info(f"Failed to parse model data price:\n {model}")
                input_cost = 0
                output_cost = 0

            formatted_model = {
                "name": model.get('id'),
                "provider": "open_router",
                "is_think": True,  # Defaulting to True - this should be deprecated anyways
                "input_cost": input_cost,
                "output_cost": output_cost,
                "context_tokens": model.get('context_length', 0),
                "created": model.get('created', 0)
            }
            if formatted_model["name"]:
                formatted_models.append(formatted_model)

    except httpx.RequestError as e:
        logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return []

    return formatted_models
