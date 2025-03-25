#!/usr/bin/env python3

"""
Utility for loading and managing prompts from files.
"""
from pathlib import Path
import textwrap
from typing import Dict


class PromptManager:
    """
    Manager for loading and caching prompts from files.
    """

    _prompt_cache: Dict[str, str] = {}

    @classmethod
    def load(cls, prompt_name: str) -> str:
        """
        Load a prompt by name from the prompts directory.

        Args:
            prompt_name: Name of the prompt file (without extension)

        Returns:
            str: Content of the prompt file
        """
        if prompt_name not in cls._prompt_cache:
            prompt_dir = Path(__file__).parent
            for prompt_file in prompt_dir.rglob(f"{prompt_name}.md"):
                with open(prompt_file, "r") as f:
                    cls._prompt_cache[prompt_name] = textwrap.dedent(f.read())
        return cls._prompt_cache.get(prompt_name, "")
