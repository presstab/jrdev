import json
import logging
import os
from typing import Any, Dict, List, Optional

from jrdev.file_operations.file_utils import JRDEV_DIR, JRDEV_PACKAGE_DIR

# Get the global logger instance
logger = logging.getLogger("jrdev")


class ModelProfileManager:
    """
    Manages model profiles for different task types.
    Profiles are stored in a JSON configuration file.
    """

    def __init__(self, config_path: Optional[str] = None, 
                 profile_strings_path: Optional[str] = None,
                 providers_path: Optional[str] = None,
                 active_provider_names: Optional[List[str]] = None):
        """
        Initialize the profile manager.

        Args:
            config_path: Optional path to the JSON configuration file.
                         If not provided, uses the default in JRDEV_DIR.
            profile_strings_path: Optional path to the profile strings JSON file.
                                  If not provided, uses the default in config directory.
            providers_path: Optional path to the api_providers.json file.
                            If not provided, uses default in config directory.
            active_provider_names: Optional list of provider names with active API keys.
        """
        # Initialize the configuration path
        self.config_path: str = os.path.join(JRDEV_DIR, "model_profiles.json")
        if config_path is not None:
            self.config_path = config_path

        # Create JRDEV_DIR if it doesn't exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        # Initialize profile strings path
        self.profile_strings_path: str
        if profile_strings_path is not None:
            self.profile_strings_path = profile_strings_path
        else:
            self.profile_strings_path = os.path.join(
                JRDEV_PACKAGE_DIR,
                "config",
                "profile_strings.json"
            )

        # Initialize providers path
        self.providers_path: str
        if providers_path is not None:
            self.providers_path = providers_path
        else:
            self.providers_path = os.path.join(
                JRDEV_PACKAGE_DIR,
                "config",
                "api_providers.json"
            )
        
        self.active_provider_names: List[str] = active_provider_names if active_provider_names is not None else []
        self.provider_preference_order: List[str] = ["open_router", "openai", "anthropic", "venice", "deepseek"]

        self.profiles = self._load_profiles()
        self.profile_strings = self._load_profile_strings()

    def _load_profiles(self, remove_fallback=False) -> Dict[str, Any]:
        """
        Load profile configuration from JSON. If the user's config file doesn't exist,
        it attempts to create one using defaults from an active provider based on
        `provider_preference_order`. If that fails, it uses hardcoded defaults.

        Returns:
            Dictionary containing profiles configuration
        """
        hardcoded_fallback_config: Dict[str, Any] = {
            "profiles": {
                "advanced_reasoning": "deepseek-r1-671b",
                "advanced_coding": "deepseek-r1-671b",
                "intermediate_reasoning": "llama-3.3-70b",
                "intermediate_coding": "qwen-2.5-coder-32b",
                "quick_reasoning": "qwen-2.5-coder-32b",
            },
            "default_profile": "advanced_coding",
            # chat_model will be derived from default_profile
        }
        hardcoded_fallback_config["chat_model"] = hardcoded_fallback_config["profiles"].get(
            hardcoded_fallback_config["default_profile"], "deepseek-r1-671b" # Ultimate fallback for chat_model
        )

        try:
            if not remove_fallback and os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config: Dict[str, Any] = json.load(f)

                if not all(key in config for key in ["profiles", "default_profile", "chat_model"]):
                    logger.warning(
                        f"Profile configuration {self.config_path} missing required fields. Re-creating with defaults."
                    )
                    # Fall through to default creation logic by not returning here
                else:
                    logger.info(f"Successfully loaded profile configuration from {self.config_path}")
                    return config
            
            # Config file does not exist or was invalid; create a new default one.
            logger.info(
                f"Profile configuration file {self.config_path} not found or invalid. Attempting to create one."
            )
            
            determined_default_config: Optional[Dict[str, Any]] = None

            if self.providers_path and os.path.exists(self.providers_path) and self.active_provider_names:
                logger.info(f"Attempting to load defaults from providers specified in {self.providers_path}")
                try:
                    with open(self.providers_path, "r") as f_providers:
                        providers_data = json.load(f_providers)
                    
                    all_provider_configs = providers_data.get("providers", [])
                    
                    for preferred_provider_name in self.provider_preference_order:
                        if preferred_provider_name in self.active_provider_names:
                            provider_config_entry = next((p for p in all_provider_configs if p.get("name") == preferred_provider_name), None)
                            
                            if provider_config_entry and "default_profiles" in provider_config_entry:
                                provider_defaults = provider_config_entry["default_profiles"]
                                if isinstance(provider_defaults, dict) and \
                                   "profiles" in provider_defaults and isinstance(provider_defaults["profiles"], dict) and \
                                   "default_profile" in provider_defaults and isinstance(provider_defaults["default_profile"], str):
                                    
                                    determined_default_config = provider_defaults.copy()
                                    default_profile_key = determined_default_config["default_profile"]
                                    
                                    if default_profile_key in determined_default_config["profiles"]:
                                        determined_default_config["chat_model"] = determined_default_config["profiles"][default_profile_key]
                                    elif determined_default_config["profiles"]: # If default_profile key is bad, use first available
                                        logger.warning(f"Default profile '{default_profile_key}' not found in profiles for provider '{preferred_provider_name}'. Using first available profile model as chat_model.")
                                        determined_default_config["chat_model"] = next(iter(determined_default_config["profiles"].values()))
                                    else: # No profiles defined, cannot use this provider's defaults
                                        logger.warning(f"Provider '{preferred_provider_name}' has empty 'profiles' in 'default_profiles'. Skipping.")
                                        determined_default_config = None
                                        continue

                                    logger.info(f"Using default profiles from active provider: {preferred_provider_name}")
                                    break # Found a suitable provider default
                                else:
                                    logger.warning(f"Provider '{preferred_provider_name}' has malformed 'default_profiles' structure. Skipping.")
                except Exception as e:
                    logger.warning(f"Error reading or parsing providers_path '{self.providers_path}': {e}. Will use hardcoded defaults if necessary.")

            final_config_to_save: Dict[str, Any]
            if determined_default_config:
                final_config_to_save = determined_default_config
                logger.info(f"Selected provider-based defaults for {self.config_path}.")
            else:
                final_config_to_save = hardcoded_fallback_config
                logger.info(f"No suitable active provider default found or providers_path not configured. Using hardcoded default profiles for {self.config_path}.")

            with open(self.config_path, "w") as f:
                json.dump(final_config_to_save, f, indent=2)
            logger.info(f"Created default profile configuration at {self.config_path}")
            return final_config_to_save

        except Exception as e:
            logger.error(f"Critical error loading or creating profile configuration: {str(e)}. Returning emergency hardcoded defaults.")
            return hardcoded_fallback_config

    def _load_profile_strings(self) -> Dict[str, Dict[str, Any]]:
        """
        Load profile strings from JSON configuration file.

        Returns:
            Dictionary mapping profile names to their metadata (description, purpose, usage)
        """
        default_strings: Dict[str, Dict[str, Any]] = {}

        try:
            if os.path.exists(self.profile_strings_path):
                with open(self.profile_strings_path, "r") as f:
                    data = json.load(f)
                    profiles = data.get("profiles", [])
                    return {p["name"]: p for p in profiles}
            else:
                logger.warning(
                    f"Profile strings file {self.profile_strings_path} not found, using empty defaults"
                )
                return default_strings

        except Exception as e:
            logger.error(f"Error loading profile strings: {str(e)}")
            return default_strings

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
            from jrdev.models.model_list import ModelList
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

    def get_profile_description(self, profile_name: str) -> str:
        """
        Get the description for a profile.

        Args:
            profile_name: The profile name to look up

        Returns:
            The description of the profile or empty string if not found
        """
        profile_data = self.profile_strings.get(profile_name, {})
        return str(profile_data.get("description", ""))

    def get_profile_purpose(self, profile_name: str) -> str:
        """
        Get the purpose for a profile.

        Args:
            profile_name: The profile name to look up

        Returns:
            The purpose of the profile or empty string if not found
        """
        profile_data = self.profile_strings.get(profile_name, {})
        return str(profile_data.get("purpose", ""))

    def get_profile_usage(self, profile_name: str) -> List[str]:
        """
        Get the usage list for a profile.

        Args:
            profile_name: The profile name to look up

        Returns:
            List of usage contexts for the profile or empty list if not found
        """
        profile_data = self.profile_strings.get(profile_name, {})
        usage = profile_data.get("usage", [])
        return [str(item) for item in usage] if isinstance(usage, list) else []

    def get_profile_data(self, profile_name: str) -> Dict[str, Any]:
        """
        Get all metadata for a profile.

        Args:
            profile_name: The profile name to look up

        Returns:
            Dictionary containing all profile metadata or empty dict if not found
        """
        return self.profile_strings.get(profile_name, {})

    def reload_if_using_fallback(self, active_provider_names) -> bool:
        """
        Reload the profiles if the current profiles match the hardcoded fallback config.
        This allows the correct provider-based defaults to be loaded after API keys are entered.
        Returns True if reload occurred, False otherwise.
        """
        self.active_provider_names: List[str] = active_provider_names if active_provider_names is not None else []
        hardcoded_fallback_config = {
            "profiles": {
                "advanced_reasoning": "deepseek-r1-671b",
                "advanced_coding": "deepseek-r1-671b",
                "intermediate_reasoning": "llama-3.3-70b",
                "intermediate_coding": "qwen-2.5-coder-32b",
                "quick_reasoning": "qwen-2.5-coder-32b",
            },
            "default_profile": "advanced_coding",
        }
        hardcoded_fallback_config["chat_model"] = hardcoded_fallback_config["profiles"].get(
            hardcoded_fallback_config["default_profile"], "deepseek-r1-671b"
        )
        # Only compare the relevant keys
        current = self.profiles
        is_fallback = (
            current.get("profiles") == hardcoded_fallback_config["profiles"] and
            current.get("default_profile") == hardcoded_fallback_config["default_profile"] and
            current.get("chat_model") == hardcoded_fallback_config["chat_model"]
        )
        if is_fallback:
            new_profiles = self._load_profiles(remove_fallback=True)
            self.profiles = new_profiles
            try:
                with open(self.config_path, "w") as f:
                    json.dump(self.profiles, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to write reloaded profiles to file: {e}")
            logger.info("Reloaded profiles from provider-based defaults after detecting fallback config.")
            return True
        return False
