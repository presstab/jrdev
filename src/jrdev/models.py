#!/usr/bin/env python3

"""
Models configuration for the JrDev terminal.
"""
import asyncio
import os
import time
import logging
from typing import Dict, List, Any
from openai import AsyncOpenAI

from jrdev.model_list import ModelList

# Get the global logger
logger = logging.getLogger("jrdev")


async def fetch_venice_models(client: AsyncOpenAI) -> List[Dict[str, Any]]:
    """
    Fetch available models from Venice API.
    
    Args:
        client: AsyncOpenAI client to use for the request
        
    Returns:
        List of models in the JrDev format, or None if the API call fails
    """
    api_key = os.getenv("VENICE_API_KEY")
    if not api_key:
        logger.warning("VENICE_API_KEY not found in environment, using hardcoded models")
        return None

    try:
        # Make the API request - using models.list() method instead of raw_response
        response = await client.models.list()
        
        if not response.data:
            logger.error("No models returned from Venice API")
            return None
        
        jrdev_models = []
        
        # Process text models from the API response
        for model in response.data:
            # Skip non-text models
            if getattr(model, "type", None) != "text":
                continue
            
            # Get model details
            model_id = model.id
            model_spec = getattr(model, "model_spec", {})
            
            # Extract values from model_spec (handling potential missing attributes)
            available_context_tokens = (
                model_spec.get("availableContextTokens", 32768) 
                if isinstance(model_spec, dict) else 32768
            )
            
            capabilities = model_spec.get("capabilities", {}) if isinstance(model_spec, dict) else {}
            is_think = capabilities.get("supportsReasoning", False) if isinstance(capabilities, dict) else False
            
            jrdev_models.append({
                "name": model_id,
                "provider": "venice",
                "is_think": is_think,
                "input_cost": 7,
                "output_cost": 28,
                "context_tokens": available_context_tokens
            })
        
        logger.info(f"Successfully fetched {len(jrdev_models)} models from Venice API")
        return jrdev_models
            
    except Exception as e:
        logger.error(f"Error fetching Venice models: {str(e)}")
        return None
