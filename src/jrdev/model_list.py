import asyncio
import threading

class ModelList:
    def __init__(self):
        self._model_list = []
        self._lock = threading.Lock()  # Thread-safe lock

    def get_model_list(self):
        with self._lock:
            return list(self._model_list)  # return a copy to avoid race conditions

    def set_model_list(self, new_list):
        with self._lock:
            self._model_list = new_list

    def append_model_list(self, new_models):
        with self._lock:
            names = [m["name"] for m in self._model_list]
            for m in new_models:
                if m["name"] in self._model_list:
                    continue
                self._model_list.append(m)

    async def async_get_model_list(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_model_list)

    async def async_set_model_list(self, new_list):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.set_model_list, new_list)
