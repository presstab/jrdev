#!/usr/bin/env python3

"""
Models configuration for the JrDev terminal.
"""

# List of available models
AVAILABLE_MODELS = [
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
