from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import json
from pathlib import Path


@dataclass
class DefaultProfiles:
    profiles: Dict[str, str]
    default_profile: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DefaultProfiles:
        return cls(
            profiles=data["profiles"],
            default_profile=data["default_profile"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profiles": self.profiles,
            "default_profile": self.default_profile,
        }


@dataclass
class ApiProvider:
    name: str
    env_key: str
    base_url: Optional[str]
    required: bool
    default_profiles: DefaultProfiles

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApiProvider:
        return cls(
            name=data["name"],
            env_key=data["env_key"],
            base_url=data.get("base_url"),
            required=data.get("required", False),
            default_profiles=DefaultProfiles.from_dict(data["default_profiles"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "env_key": self.env_key,
            "base_url": self.base_url,
            "required": self.required,
            "default_profiles": self.default_profiles.to_dict(),
        }

def load_providers(path: Path | str) -> List[ApiProvider]:
    """
    Load all providers from a JSON file structured like api_providers.json.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [ApiProvider.from_dict(p) for p in raw.get("providers", [])]