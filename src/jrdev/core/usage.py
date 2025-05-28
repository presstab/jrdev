"""Track token usage by model."""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Optional


class Usage:
    """Track cumulative token usage per model."""

    def __init__(self, save_path: Optional[str] = None) -> None:
        """Initialize usage tracking.

        Args:
            save_path: Path to save usage data. None means no persistence.
        """
        # {model: {input_tokens: X, output_tokens: Y}}
        self._usage: Dict[str, Dict[str, int]] = {}
        self._lock = asyncio.Lock()
        self._save_path = save_path

        # Load existing data if available
        if save_path:
            self._load()

    async def add_use(self, model: str, input_tokens: int,
                      output_tokens: int) -> None:
        """Add token usage for a model.

        Args:
            model: The model identifier
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
        """
        async with self._lock:
            if model not in self._usage:
                self._usage[model] = {"input_tokens": 0, "output_tokens": 0}

            self._usage[model]["input_tokens"] += input_tokens
            self._usage[model]["output_tokens"] += output_tokens

            if self._save_path:
                await self._save()

    async def get_usage(
        self, model: Optional[str] = None
    ) -> Dict[str, Dict[str, int]]:
        """Get usage statistics.

        Args:
            model: Optional model to get stats for. If None, returns all stats.

        Returns:
            Dict containing usage statistics
        """
        async with self._lock:
            if model:
                # Return in format that matches the overall structure
                result: Dict[str, Dict[str, int]] = {}
                result[model] = self._usage.get(
                    model, {"input_tokens": 0, "output_tokens": 0})
                return result
            return self._usage.copy()

    async def reset(self, model: Optional[str] = None) -> None:
        """Reset usage statistics.

        Args:
            model: Optional model to reset. If None, resets all stats.
        """
        async with self._lock:
            if model:
                self._usage.pop(model, None)
            else:
                self._usage = {}

            if self._save_path:
                await self._save()

    def _load(self) -> None:
        """Load usage data from disk."""
        if self._save_path is None:
            return

        path = Path(self._save_path)
        if path.exists():
            try:
                with open(path, "r") as f:
                    self._usage = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._usage = {}

    async def _save(self) -> None:
        """Save usage data to disk."""
        if not self._save_path:
            return

        try:
            path = Path(self._save_path)
            # Ensure directory exists
            os.makedirs(path.parent, exist_ok=True)

            # Write to a temporary file first, then rename for atomicity
            temp_path = f"{self._save_path}.tmp"
            with open(temp_path, "w") as f:
                json.dump(self._usage, f, indent=2)

            # Atomic rename
            os.replace(temp_path, self._save_path)
        except IOError:
            # Just log the error and continue - don't want to crash the app
            # for usage tracking failures
            pass


# Global instance for convenient access
_instance: Optional[Usage] = None


def get_instance(save_path: Optional[str] = None) -> Usage:
    """Get the global Usage instance.

    Args:
        save_path: Optional path to save usage data

    Returns:
        Global Usage instance
    """
    global _instance
    if _instance is None:
        _instance = Usage(save_path)
    return _instance