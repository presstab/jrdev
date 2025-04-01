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

    def append_model_list(self, new_models: List[Dict[str, Any]]) -> None:
        with self._lock:
            names = [m["name"] for m in self._model_list]
            for m in new_models:
                if m["name"] in self._model_list:
                    continue
                self._model_list.append(m)

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

    async def async_get_model_list(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_model_list)

    async def async_set_model_list(self, new_list: List[Dict[str, Any]]) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.set_model_list, new_list)
