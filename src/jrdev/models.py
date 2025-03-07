#!/usr/bin/env python3

"""
Models configuration for the JrDev terminal.
"""

# List of available models
AVAILABLE_MODELS = [
    {
        "name": "deepseek-r1-671b",
        "is_think": True,
        "input_cost": 35,
        "output_cost": 140
    },
    {
        "name": "deepseek-r1-llama-70b",
        "is_think": True,
        "input_cost": 7,
        "output_cost": 28
    },
    {
        "name": "qwen-2.5-coder-32b",
        "is_think": False,
        "input_cost": 5,
        "output_cost": 20
    },
    {
        "name": "qwen-2.5-qwq-32b",
        "is_think": True,
        "input_cost": 5,
        "output_cost": 20
    },
    {
        "name": "llama-3.3-70b",
        "is_think": False,
        "input_cost": 7,
        "output_cost": 28
    },
    {
        "name": "llama-3.1-405b",
        "is_think": False,
        "input_cost": 15,
        "output_cost": 60
    },
    {
        "name": "llama-3.2-3b",
        "is_think": False,
        "input_cost": 2,
        "output_cost": 6
    }
]


def is_think_model(model):
    for entry in AVAILABLE_MODELS:
        if entry["name"] == model:
            return entry["is_think"]

    return False