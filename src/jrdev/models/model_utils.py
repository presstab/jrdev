#!/usr/bin/env python3

"""
Utility functions for model management in JrDev.
"""
import json
import logging
import os
from typing import Dict, List, Any

# Get the global logger
logger = logging.getLogger("jrdev")

def load_hardcoded_models() -> List[Dict[str, Any]]:
    """
    Load hardcoded models from JSON file.

    Returns:
        List of hardcoded models
    """
    try:
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Navigate up one level to jrdev/, then into config/
        json_path = os.path.join(current_dir, "..", "config", "model_list.json")

        with open(json_path, "r") as f:
            data = json.load(f)
            return data["models"]
    except Exception as e:
        logger.error(f"Error loading hardcoded models: {e}")
        # Return empty list as fallback
        return []

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
