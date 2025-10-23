from importlib import import_module
from typing import Any

__all__ = ["CommandInterpretationAgent"]


def __getattr__(name: str) -> Any:
    if name == "CommandInterpretationAgent":
        return import_module("jrdev.agents.router_agent").CommandInterpretationAgent
    raise AttributeError(name)
