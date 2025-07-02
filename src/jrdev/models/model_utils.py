#!/usr/bin/env python3

"""
Utility functions for model management in JrDev.
Models are managed via a user-specific configuration file (user_models.json),
which acts as the single source of truth. If this file doesn't exist,
it's created using defaults from the system's model_list.json.
"""
import json
import logging
import os
from typing import Dict, List, Any, Optional

from jrdev.file_operations.file_utils import JRDEV_PACKAGE_DIR, get_persistent_storage_path

# Get the global logger
logger = logging.getLogger("jrdev")

USER_MODELS_FILENAME = "user_models.json"

def _get_user_models_config_path() -> str:
    """Helper function to get the full path to the user models config file."""
    persistent_storage_path = get_persistent_storage_path()
    return os.path.join(persistent_storage_path, USER_MODELS_FILENAME)

def _get_default_models_from_system_config() -> List[Dict[str, Any]]:
    """
    Loads the default list of models from the system's configuration file.
    This is used as the initial content for the user's model config if it doesn't exist.

    Returns:
        List of model dictionaries from 'src/jrdev/config/model_list.json'.
    """
    try:
        json_path = os.path.join(JRDEV_PACKAGE_DIR, "config", "model_list.json")
        with open(json_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            models = data.get("models", [])
            if not isinstance(models, list):
                logger.error(f"Default models data in {json_path} is not a list. Returning empty list.")
                return []
            return models
    except FileNotFoundError:
        logger.error(f"System default models file not found at {json_path}. Returning empty list.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding system default models JSON from {json_path}: {e}. Returning empty list.")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading system default models from {json_path}: {e}. Returning empty list.")
        return []

def _ensure_user_models_config_exists() -> None:
    """
    Ensures the user's model configuration file (user_models.json) exists.
    If not, it creates one by copying the structure and content from the
    system default 'model_list.json'. The models are stored under a 'models' key.
    """
    user_config_path = _get_user_models_config_path()
    if not os.path.exists(user_config_path):
        logger.info(f"User models config file not found at {user_config_path}. Creating from system defaults.")
        default_models = _get_default_models_from_system_config()
        try:
            os.makedirs(os.path.dirname(user_config_path), exist_ok=True)
            with open(user_config_path, "w", encoding='utf-8') as f:
                json.dump({"models": default_models}, f, indent=4)
            logger.info(f"Successfully created user models config at {user_config_path} with {len(default_models)} models.")
        except Exception as e:
            logger.error(f"Failed to create user models config file at {user_config_path}: {e}")

def load_models() -> List[Dict[str, Any]]:
    """
    Loads the list of AI models from the user's configuration file (user_models.json).
    This function first ensures the user's config file exists by calling
    _ensure_user_models_config_exists(). The user's config file is the single source of truth.

    Returns:
        List of model dictionaries from the user's 'user_models.json'.
    """
    _ensure_user_models_config_exists()

    user_config_path = _get_user_models_config_path()
    try:
        with open(user_config_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            models = data.get("models", [])
            # Basic validation
            if not isinstance(models, list) or not all(isinstance(m, dict) and "name" in m for m in models):
                logger.warning(f"Models data in {user_config_path} is malformed or missing 'name' fields. Returning empty list.")
                # Optionally, attempt to repair or re-create from defaults here, or just return empty
                return []
            logger.debug(f"Loaded {len(models)} models from user config: {user_config_path}")
            return models
    except FileNotFoundError: # Should be handled by _ensure, but as a safeguard
        logger.error(f"User models config file {user_config_path} not found despite ensure check. Returning empty list.")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from user models config {user_config_path}. Returning empty list.")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading models from {user_config_path}: {e}. Returning empty list.")
        return []

def save_models(models_list: List[Dict[str, Any]]) -> None:
    """
    Saves the provided list of models to the user's 'user_models.json' file,
    overwriting its previous content. The models are stored under a "models" key.

    Args:
        models_list: The list of model dictionaries to save.
    """
    user_config_path = _get_user_models_config_path()
    try:
        os.makedirs(os.path.dirname(user_config_path), exist_ok=True)
        with open(user_config_path, "w", encoding='utf-8') as f:
            json.dump({"models": models_list}, f, indent=4)
        logger.info(f"Successfully saved {len(models_list)} models to user config: {user_config_path}")
    except Exception as e:
        logger.error(f"Error saving models to user config {user_config_path}: {e}")

def get_model_cost(model_name: str, available_models: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """
    Get model input and output cost per million tokens (cost denominated per million tokens).

    Args:
        model_name: Name of the model to get costs for.
        available_models: List of available models (typically from load_models()).

    Returns:
        Dictionary with input_cost and output_cost, or None if model not found.
    """
    for entry in available_models:
        if entry.get("name") == model_name:
            input_cost = entry.get("input_cost", 0)
            output_cost = entry.get("output_cost", 0)
            if not isinstance(input_cost, int):
                logger.warning(f"Model '{model_name}' has non-integer input_cost '{input_cost}'. Defaulting to 0.")
                input_cost = 0
            if not isinstance(output_cost, int):
                logger.warning(f"Model '{model_name}' has non-integer output_cost '{output_cost}'. Defaulting to 0.")
                output_cost = 0
            # costs are stored per 100k tokens, covert to million
            scale = Price_Per_Token_Scale()
            return {"input_cost": input_cost * scale, "output_cost": output_cost * scale}
    logger.debug(f"Model '{model_name}' not found in available models for cost lookup.")
    return None

def is_think_model(model_name: str, available_models: List[Dict[str, Any]]) -> bool:
    """
    Check if a model is a "think" model.

    Args:
        model_name: Name of the model to check.
        available_models: List of available models (typically from load_models()).

    Returns:
        True if the model is a think model, False otherwise or if model not found.
    """
    for entry in available_models:
        if entry.get("name") == model_name:
            is_think = entry.get("is_think", False)
            if not isinstance(is_think, bool):
                logger.warning(f"Model '{model_name}' has non-boolean is_think value '{is_think}'. Defaulting to False.")
                return False
            return is_think
    logger.debug(f"Model '{model_name}' not found in available models for is_think lookup.")
    return False

def Price_Per_Token_Scale() -> float:
    """Token price storage is scaled. Multiply the price per token by this."""
    return 0.1
