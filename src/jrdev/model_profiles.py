import json
import logging
import os
from typing import Any, Dict, Optional

from jrdev.file_utils import JRDEV_DIR
from jrdev.ui.ui import PrintType

# Get the global logger instance
logger = logging.getLogger("jrdev")


class ModelProfileManager:
    """
    Manages model profiles for different task types.
    Profiles are stored in a JSON configuration file.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the profile manager with a path to the config file.

        Args:
            config_path: Optional path to the JSON configuration file.
                         If not provided, uses the default in JRDEV_DIR.
        """
        # Initialize the configuration path
        self.config_path: str = os.path.join(JRDEV_DIR, "model_profiles.json")

        if config_path is not None:
            self.config_path = config_path

        # Create JRDEV_DIR if it doesn't exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        self.profiles = self._load_profiles()

    def _load_profiles(self) -> Dict[str, Any]:
        """
        Load profile configuration from JSON with fallback to defaults.

        Returns:
            Dictionary containing profiles configuration
        """
        default_config: Dict[str, Any] = {
            "profiles": {
                "advanced_reasoning": "deepseek-r1-671b",
                "advanced_coding": "deepseek-r1-671b",
                "intermediate_reasoning": "llama-3.3-70b",
                "intermediate_coding": "qwen-2.5-coder-32b",
                "quick_reasoning": "qwen-2.5-coder-32b",
            },
            "default_profile": "advanced_coding",
        }

        try:
            # Check if the config file exists
            if os.path.exists(self.config_path):
                config_path = self.config_path
            else:
                logger.warning(
                    f"Profile configuration file {self.config_path} not found, using defaults"
                )
                # Save the default config for future use
                with open(self.config_path, "w") as f:
                    json.dump(default_config, f, indent=2)
                logger.info(
                    f"Created default profile configuration at {self.config_path}"
                )
                return default_config

            with open(config_path, "r") as f:
                config: Dict[str, Any] = json.load(f)

            # Validate loaded config has required fields
            if not all(key in config for key in ["profiles", "default_profile"]):
                logger.warning(
                    "Profile configuration missing required fields, using defaults"
                )
                return default_config

            logger.info(f"Successfully loaded profile configuration from {config_path}")
            return config

        except Exception as e:
            logger.error(f"Error loading profile configuration: {str(e)}")
            # Error log only, UI feedback handled by caller
            return default_config

    def get_model(self, profile_type: str) -> str:
        """
        Get model name for the specified profile type.

        Args:
            profile_type: The profile type to look up

        Returns:
            The model name associated with the profile
        """
        if profile_type in self.profiles["profiles"]:
            return str(self.profiles["profiles"][profile_type])

        # Fall back to default profile if requested profile doesn't exist
        default = str(self.profiles["default_profile"])
        logger.warning(f"Profile '{profile_type}' not found, using default: {default}")
        return str(self.profiles["profiles"].get(default, "qwen-2.5-coder-32b"))

    def update_profile(self, profile_type: str, model_name: str, model_list: Optional[Any] = None) -> bool:
        """
        Update a profile to use a different model.

        Args:
            profile_type: The profile type to update
            model_name: The model name to assign to the profile
            model_list: Optional ModelList instance for validation

        Returns:
            True if update successful, False otherwise
        """
        # Import ModelList only if needed for validation
        if model_list is None:
            from jrdev.model_list import ModelList
            # Create ModelList to validate the model exists
            model_list = ModelList()
        
        # Validate that the model exists
        if not model_list.validate_model_exists(model_name):
            # Check if it's one of the profiles in model_profiles.json
            # This allows handling special model names in the profile settings
            for profile_model in self.profiles["profiles"].values():
                if model_name == profile_model:
                    # Skip validation for models that are already in the profiles
                    logger.info(f"Accepting model '{model_name}' which exists in profiles")
                    break
            else:
                # Model is not in profiles either, report error
                logger.error(f"Model '{model_name}' does not exist in available models. Options:")
                for model in model_list.get_model_list():
                    logger.error(f"{model}")

                return False

        if not model_name:
            logger.error("Invalid model name")
            return False

        try:
            # Update the profile
            self.profiles["profiles"][profile_type] = model_name

            # Save the updated configuration
            with open(self.config_path, "w") as f:
                json.dump(self.profiles, f, indent=2)

            logger.info(f"Updated profile '{profile_type}' to use model '{model_name}'")
            return True

        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            return False

    def list_available_profiles(self) -> Dict[str, str]:
        """
        Return all available profile:model mappings.

        Returns:
            Dictionary of profile types mapped to model names
        """
        # Ensure we return a dict with string keys and string values
        return {str(k): str(v) for k, v in self.profiles["profiles"].items()}

    def get_default_profile(self) -> str:
        """
        Get the name of the default profile.

        Returns:
            The name of the default profile
        """
        return str(self.profiles["default_profile"])

    def set_default_profile(self, profile_type: str) -> bool:
        """
        Set the default profile.

        Args:
            profile_type: The profile to set as default

        Returns:
            True if successful, False otherwise
        """
        if profile_type not in self.profiles["profiles"]:
            logger.error(f"Profile '{profile_type}' does not exist")
            return False

        try:
            self.profiles["default_profile"] = profile_type

            # Save the updated configuration
            with open(self.config_path, "w") as f:
                json.dump(self.profiles, f, indent=2)

            logger.info(f"Set default profile to '{profile_type}'")
            return True

        except Exception as e:
            logger.error(f"Error setting default profile: {str(e)}")
            return False
