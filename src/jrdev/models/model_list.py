import asyncio
import threading
from typing import List, Dict, Any, Optional, Union

class ModelList:
    def __init__(self) -> None:
        self._model_list: List[Dict[str, Any]] = []
        self._lock = threading.Lock()  # Thread-safe lock

    def get_model_list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._model_list)  # return a copy to avoid race conditions

    def set_model_list(self, new_list: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._model_list = new_list

    def set_providers(self, providers: List[str]) -> None:
        """Update the model list to only include models under the given list of providers"""
        with self._lock:
            updated_list = []
            for m in self._model_list:
                if m["provider"] not in providers:
                    continue
                updated_list.append(m)
            self._model_list = updated_list

    def validate_model_exists(self, model_name: str) -> bool:
        """
        Check if a model exists in the model list.
        
        Args:
            model_name: The model name to validate
            
        Returns:
            True if the model exists, False otherwise
        """
        with self._lock:
            return any(m["name"] == model_name for m in self._model_list)

    def remove_model(self, model_name: str) -> bool:
        """
        Remove a model with the given name from the model list.
        Returns True if a model was removed, False if no such model was found.
        """
        with self._lock:
            for i, m in enumerate(self._model_list):
                if m["name"] == model_name:
                    del self._model_list[i]
                    return True
            return False

    def update_model(self, model_name: str, provider: str, is_think: bool, input_cost: int, output_cost: int, context_window: int) -> bool:
        """
        Update an existing model in the model list.
        Args:
            model_name: The name of the model to update (must exist)
            provider: The provider of the model
            is_think: Whether the model is a 'think' model
            input_cost: The input cost of the model
            output_cost: The output cost of the model
            context_window: The context window (context_tokens) of the model
        Returns:
            True if the model was updated, False if the model was not found.
        """
        with self._lock:
            for m in self._model_list:
                if m["name"] == model_name:
                    # Update the model attributes
                    m["provider"] = provider
                    m["is_think"] = is_think
                    m["input_cost"] = input_cost
                    m["output_cost"] = output_cost
                    m["context_tokens"] = context_window
                    return True
            return False

    def add_model(self, model_name: str, provider: str, is_think: bool, input_cost: int, output_cost: int, context_window: int) -> bool:
        """
        Add a new model to the model list if it does not already exist.
        Args:
            model_name: The name of the model to add
            provider: The provider of the model
            is_think: Whether the model is a 'think' model
            input_cost: The input cost of the model
            output_cost: The output cost of the model
            context_window: The context window (context_tokens) of the model
        Returns:
            True if the model was added, False if a model with the same name already exists
        """
        with self._lock:
            if any(m["name"] == model_name for m in self._model_list):
                return False
            model_dict = {
                "name": model_name,
                "provider": provider,
                "is_think": is_think,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "context_tokens": context_window
            }
            self._model_list.append(model_dict)
            return True