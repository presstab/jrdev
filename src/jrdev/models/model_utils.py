#!/usr/bin/env python3

"""
Utility functions for model management in JrDev.
"""
import json
import logging
import os
from typing import Dict, List, Any

from jrdev.file_operations.file_utils import JRDEV_PACKAGE_DIR, get_persistent_storage_path

# Get the global logger
logger = logging.getLogger("jrdev")

USER_MODEL_CONFIG_FILENAME = "user_model_config.json"

def _get_user_config_path() -> str:
    """Helper function to get the full path to the user model config file."""
    persistent_storage_path = get_persistent_storage_path()
    return os.path.join(persistent_storage_path, USER_MODEL_CONFIG_FILENAME)

def _load_user_config() -> Dict[str, Any]:
    """Loads the user model configuration from JSON file.

    Returns:
        A dictionary containing 'user_models' and 'ignored_model_names'.
        Returns default empty lists if file not found or parsing error.
    """
    user_config_path = _get_user_config_path()
    default_config = {"user_models": [], "ignored_model_names": []}

    if not os.path.exists(user_config_path):
        logger.info(f"User model config {user_config_path} not found. Using default empty config.")
        return default_config
    
    try:
        with open(user_config_path, "r", encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Validate and normalize structure
        if not isinstance(config_data.get("user_models"), list) or \
           not all(isinstance(m, dict) and "name" in m for m in config_data.get("user_models", [])):
            logger.warning(f"'user_models' in {user_config_path} is malformed. Resetting to empty list.")
            config_data["user_models"] = []

        if not isinstance(config_data.get("ignored_model_names"), list) or \
           not all(isinstance(name, str) for name in config_data.get("ignored_model_names", [])):
            logger.warning(f"'ignored_model_names' in {user_config_path} is malformed. Resetting to empty list.")
            config_data["ignored_model_names"] = []
            
        return config_data
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {user_config_path}. Returning default config.")
        return default_config
    except Exception as e:
        logger.error(f"Unexpected error loading user model config {user_config_path}: {e}. Returning default config.")
        return default_config

def _save_user_config(config_data: Dict[str, Any]) -> None:
    """Saves the user model configuration to JSON file.

    Args:
        config_data: Dictionary containing 'user_models' and 'ignored_model_names'.
    """
    user_config_path = _get_user_config_path()
    try:
        os.makedirs(os.path.dirname(user_config_path), exist_ok=True)
        with open(user_config_path, "w", encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        logger.info(f"User model configuration saved to {user_config_path}")
    except Exception as e:
        logger.error(f"Error saving user model configuration to {user_config_path}: {e}")

def load_hardcoded_models() -> List[Dict[str, Any]]:
    """
    Load hardcoded models from JSON file.

    Returns:
        List of hardcoded models
    """
    try:
        json_path = os.path.join(JRDEV_PACKAGE_DIR, "config", "model_list.json")

        with open(json_path, "r") as f:
            data = json.load(f)
            return data.get("models", [])
    except FileNotFoundError:
        logger.error(f"Hardcoded models file not found at {json_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding hardcoded models JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading hardcoded models: {e}")
        # Return empty list as fallback
        return []

def get_ignored_model_names() -> List[str]:
    """
    Retrieves the list of model names that the user has marked as ignored.

    Returns:
        A list of strings, where each string is an ignored model name.
    """
    config = _load_user_config()
    return config.get("ignored_model_names", [])

def ignore_model(model_name: str) -> bool:
    """
    Adds a model to the ignored list and removes it from the active user models list
    in the configuration file. The change is persisted to user_model_config.json.

    Args:
        model_name: The name of the model to ignore.

    Returns:
        True if the model was successfully ignored, False if it was already ignored.
    """
    config = _load_user_config()
    user_models = config.get("user_models", [])
    ignored_names = config.get("ignored_model_names", [])

    if model_name in ignored_names:
        logger.info(f"Model '{model_name}' is already in the ignored list.")
        return False

    ignored_names.append(model_name)
    updated_user_models = [m for m in user_models if m.get("name") != model_name]
    
    if len(user_models) != len(updated_user_models):
        logger.info(f"Model '{model_name}' marked for removal from active user models list in config.")
    
    _save_user_config({
        "user_models": updated_user_models,
        "ignored_model_names": sorted(list(set(ignored_names)))
    })
    logger.info(f"Model '{model_name}' added to ignored list in config.")
    return True

def unignore_model(model_name: str) -> bool:
    """
    Removes a model from the ignored list in the configuration file.
    The change is persisted to user_model_config.json.
    The model may be re-added to the active list by load_user_preferred_models
    during the next model list refresh if it's a default model.

    Args:
        model_name: The name of the model to unignore.

    Returns:
        True if the model was successfully unignored, False if it was not in the ignored list.
    """
    config = _load_user_config()
    ignored_names = config.get("ignored_model_names", [])

    if model_name not in ignored_names:
        logger.info(f"Model '{model_name}' is not in the ignored list.")
        return False

    ignored_names.remove(model_name)
    
    _save_user_config({
        "user_models": config.get("user_models", []), # Pass through existing user_models
        "ignored_model_names": sorted(list(set(ignored_names)))
    })
    logger.info(f"Model '{model_name}' removed from ignored list in config. It may become available after model list refresh.")
    return True

def load_user_preferred_models() -> List[Dict[str, Any]]:
    """
    Loads the user's preferred model list, synchronizing it with hardcoded models
    and respecting the user's ignored models list.
    User preferences are stored in user_model_config.json.

    Returns:
        List of model dictionaries representing the final available models.
    """
    default_models = load_hardcoded_models()
    user_config = _load_user_config()
    
    user_models_from_file = user_config.get("user_models", [])
    ignored_model_names_from_file = user_config.get("ignored_model_names", [])
    
    config_needs_saving = False

    synced_user_models = [model.copy() for model in user_models_from_file]
    final_ignored_model_names = sorted(list(set(ignored_model_names_from_file))) # Ensure unique and sorted

    # Check if ignored_model_names_from_file was changed by sorting/deduplicating
    if final_ignored_model_names != ignored_model_names_from_file:
        config_needs_saving = True

    current_user_model_names = {model["name"] for model in synced_user_models if "name" in model}

    if not user_models_from_file and default_models:
        logger.info("User model list in config is empty; will populate with defaults unless models are ignored.")
        # config_needs_saving will be set when models are added below

    for default_model in default_models:
        default_model_name = default_model.get("name")
        if not default_model_name:
            logger.warning(f"Default model found without a name: {default_model}. Skipping.")
            continue

        if default_model_name in final_ignored_model_names:
            if default_model_name in current_user_model_names:
                synced_user_models = [m for m in synced_user_models if m.get("name") != default_model_name]
                current_user_model_names.remove(default_model_name)
                config_needs_saving = True
                logger.info(f"Model '{default_model_name}' is ignored by user, removed from active list.")
            continue # Skip if ignored

        if default_model_name not in current_user_model_names:
            synced_user_models.append(default_model.copy())
            current_user_model_names.add(default_model_name)
            config_needs_saving = True
            logger.info(f"New model '{default_model_name}' added to user's list from defaults.")
        else:
            # Model exists in user's list; update its properties from default_model
            for i, user_model_instance in enumerate(synced_user_models):
                if user_model_instance.get("name") == default_model_name:
                    model_updated_from_default = False
                    for key, default_value in default_model.items():
                        if user_model_instance.get(key) != default_value:
                            user_model_instance[key] = default_value
                            model_updated_from_default = True
                    
                    if model_updated_from_default:
                        synced_user_models[i] = user_model_instance
                        config_needs_saving = True
                        logger.info(f"Updated properties for model '{default_model_name}' in user's list from defaults.")
                    break
    
    # Deduplicate final list (e.g. if user manually added duplicates or errors occurred)
    seen_names = set()
    unique_final_models = []
    duplicates_found = False
    for model in synced_user_models:
        model_name = model.get("name")
        if model_name and model_name not in seen_names:
            unique_final_models.append(model)
            seen_names.add(model_name)
        elif model_name in seen_names:
            logger.warning(f"Duplicate model name '{model_name}' found in user's list. Keeping first instance.")
            duplicates_found = True
    
    if duplicates_found:
        config_needs_saving = True
    synced_user_models = unique_final_models

    if config_needs_saving:
        _save_user_config({"user_models": synced_user_models, "ignored_model_names": final_ignored_model_names})

    return synced_user_models

def get_model_cost(model: str, available_models: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Get model input and output cost per million tokens (cost denominated in VCU).

    Args:
        model: Name of the model to get costs for
        available_models: List of available models with their costs

    Returns:
        Dictionary with input_cost and output_cost, or None if model not found
    """
    for entry in available_models:
        if entry["name"] == model:
            return {"input_cost": entry["input_cost"], "output_cost": entry["output_cost"]}
    return None

def is_think_model(model: str, available_models: List[Dict[str, Any]]) -> bool:
    """
    Check if a model is a "think" model.

    Args:
        model: Name of the model to check
        available_models: List of available models with their properties

    Returns:
        True if the model is a think model, False otherwise
    """
    for entry in available_models:
        if entry["name"] == model:
            return entry["is_think"]
    return False

def VCU_Value() -> float:
    """Get the VCU dollar value."""
    return 0.1
