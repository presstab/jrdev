#!/usr/bin/env python3

"""
Models configuration for the JrDev terminal.
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, cast

# Get the global logger
logger = logging.getLogger("jrdev")

# Cache for Venice models to avoid frequent API calls
VENICE_MODELS_CACHE = {
    "models": None,
    "timestamp": 0,
    "cache_duration": 60 * 60  # Cache for 1 hour
}

# List of hardcoded models as fallback
HARDCODED_MODELS = [
    {
        "name": "deepseek-r1-671b",
        "provider": "venice",
        "is_think": True,
        "input_cost": 35,
        "output_cost": 140,
        "context_tokens": 131072
    },
    {
        "name": "qwen-2.5-coder-32b",
        "provider": "venice",
        "is_think": False,
        "input_cost": 5,
        "output_cost": 20,
        "context_tokens": 32768
    },
    {
        "name": "qwen-2.5-qwq-32b",
        "provider": "venice",
        "is_think": True,
        "input_cost": 5,
        "output_cost": 20,
        "context_tokens": 32768
    },
    {
        "name": "llama-3.3-70b",
        "provider": "venice",
        "is_think": False,
        "input_cost": 7,
        "output_cost": 28,
        "context_tokens": 65536
    },
    {
        "name": "llama-3.1-405b",
        "provider": "venice",
        "is_think": False,
        "input_cost": 15,
        "output_cost": 60,
        "context_tokens": 65536
    },
    {
        "name": "llama-3.2-3b",
        "provider": "venice",
        "is_think": False,
        "input_cost": 2,
        "output_cost": 6,
        "context_tokens": 131072
    },
    {
        "name": "dolphin-2.9.2-qwen2-72b",
        "provider": "venice",
        "is_think": False,
        "input_cost": 7,
        "output_cost": 28,
        "context_tokens": 32768
    },
    {
        "name": "mistral-31-24b",
        "provider": "venice",
        "is_think": False,
        "input_cost": 5,
        "output_cost": 20,
        "context_tokens": 131072
    },
    {
        "name": "o3-mini-2025-01-31",
        "provider": "openai",
        "is_think": False,
        "input_cost": 7,
        "output_cost": 28,
        "context_tokens": 32768
    },
    {
        "name": "gpt-4o",
        "provider": "openai",
        "is_think": False,
        "input_cost": 10,
        "output_cost": 30,
        "context_tokens": 128000
    },
    {
        "name": "gpt-4-turbo",
        "provider": "openai",
        "is_think": False,
        "input_cost": 10,
        "output_cost": 30,
        "context_tokens": 128000
    },
    {
        "name": "gpt-3.5-turbo",
        "provider": "openai",
        "is_think": False,
        "input_cost": 5,
        "output_cost": 15,
        "context_tokens": 16384
    }
]

# Initialize with hardcoded models
AVAILABLE_MODELS = HARDCODED_MODELS.copy()

async def fetch_venice_models() -> List[Dict[str, Any]]:
    """
    Fetch available models from Venice API.
    
    Returns:
        List of models in the JrDev format, or None if the API call fails
    """
    api_key = os.getenv("VENICE_API_KEY")
    if not api_key:
        logger.warning("VENICE_API_KEY not found in environment, using hardcoded models")
        return None

    try:
        # Use existing OpenAI client
        from openai import AsyncOpenAI
        
        # Create a client for the Venice API
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.venice.ai/api/v1"
        )
        
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
        bool: True if cache should be updated, False otherwise
    """
    current_time = time.time()
    # Update if cache is empty or expired
    return (
        VENICE_MODELS_CACHE["models"] is None or 
        current_time - VENICE_MODELS_CACHE["timestamp"] > VENICE_MODELS_CACHE["cache_duration"]
    )

async def get_available_models(force_refresh=False):
    """
    Get available models, either from cache or by fetching from API.
    
    Args:
        force_refresh: Force a refresh regardless of cache status
        
    Returns:
        List of available models
    """
    global AVAILABLE_MODELS
    
    # Check if we need to update the cache
    if force_refresh or should_update_cache():
        # Fetch models from Venice API
        venice_models = await fetch_venice_models()
        
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

def is_think_model(model):
    for entry in AVAILABLE_MODELS:
        if entry["name"] == model:
            return entry["is_think"]

    return False


def get_model_cost(model):
    """model input and output cost per million tokens (cost denominated in VCU)"""
    for entry in AVAILABLE_MODELS:
        if entry["name"] == model:
            return {"input_cost": entry["input_cost"], "output_cost": entry["output_cost"]}

    return None


def VCU_Value():
    """VCU dollar value"""
    return 0.1
