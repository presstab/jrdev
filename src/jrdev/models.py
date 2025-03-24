#!/usr/bin/env python3

"""
Models configuration for the JrDev terminal.
"""
import os
import time
import logging
from typing import Dict, List, Any
from openai import AsyncOpenAI

from jrdev.model_utils import (
    load_hardcoded_models,
    get_model_cost as get_model_cost_util,
    is_think_model as is_think_model_util,
    VCU_Value
)

# Get the global logger
logger = logging.getLogger("jrdev")

# Cache for Venice models to avoid frequent API calls
VENICE_MODELS_CACHE = {
    "models": None,
    "timestamp": 0
}

# Load hardcoded models
HARDCODED_MODELS = load_hardcoded_models()

# Initialize with hardcoded models
AVAILABLE_MODELS = HARDCODED_MODELS.copy()

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
            
            # Check for existing model in hardcoded list to get costs
            existing_model = next((m for m in HARDCODED_MODELS if m["name"] == model_id), None)
            
            # Use costs from hardcoded models if available, otherwise use defaults
            if existing_model:
                input_cost = existing_model["input_cost"]
                output_cost = existing_model["output_cost"]
            else:
                # Default costs
                input_cost = 7
                output_cost = 28
            
            jrdev_models.append({
                "name": model_id,
                "provider": "venice",
                "is_think": is_think,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "context_tokens": available_context_tokens
            })
        
        logger.info(f"Successfully fetched {len(jrdev_models)} models from Venice API")
        return jrdev_models
            
    except Exception as e:
        logger.error(f"Error fetching Venice models: {str(e)}")
        return None

def should_update_cache():
    """
    Check if the cache should be updated.
    
    Returns:
        bool: True if cache is empty, False otherwise
    """
    return VENICE_MODELS_CACHE["models"] is None

async def get_available_models(client=None, force_refresh=False):
    """
    Get available models, either from cache or by fetching from API.
    
    Args:
        client: Optional AsyncOpenAI client to use for API requests
        force_refresh: Force a refresh regardless of cache status
        
    Returns:
        List of available models
    """
    global AVAILABLE_MODELS
    
    # If no client is provided, just return the current AVAILABLE_MODELS
    if client is None:
        return AVAILABLE_MODELS
        
    # Check if we need to update the cache
    if force_refresh or should_update_cache():
        # Fetch models from Venice API
        venice_models = await fetch_venice_models(client)
        
        if venice_models:
            # Cache the fetched models
            VENICE_MODELS_CACHE["models"] = venice_models
            VENICE_MODELS_CACHE["timestamp"] = time.time()
            
            # Combine Venice models with OpenAI models from hardcoded list
            openai_models = [model for model in HARDCODED_MODELS if model["provider"] == "openai"]
            AVAILABLE_MODELS = venice_models + openai_models
        else:
            # Fall back to hardcoded models if API fetch fails
            AVAILABLE_MODELS = HARDCODED_MODELS
    
    return AVAILABLE_MODELS

def is_think_model(model: str) -> bool:
    """
    Check if a model is a "think" model.
    
    Args:
        model: Name of the model to check
        
    Returns:
        True if the model is a think model, False otherwise
    """
    return is_think_model_util(model, AVAILABLE_MODELS)

def get_model_cost(model: str) -> Dict[str, int]:
    """
    Get model input and output cost per million tokens (cost denominated in VCU).
    
    Args:
        model: Name of the model to get costs for
        
    Returns:
        Dictionary with input_cost and output_cost, or None if model not found
    """
    return get_model_cost_util(model, AVAILABLE_MODELS)
