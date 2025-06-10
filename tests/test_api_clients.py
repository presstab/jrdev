import os
import sys
import tempfile
import shutil
import json
import unittest
from pathlib import Path
from unittest.mock import patch

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.core.clients import APIClients
from jrdev.models.api_provider import ApiProvider

def make_provider_data(name, env_key=None, base_url=None):
    return {
        "name": name,
        "env_key": env_key or f"{name.upper()}_API_KEY",
        "base_url": base_url or f"https://{name}.api.com",
        "required": True,
        "default_profiles": {"profiles": {}, "default_profile": ""}
    }

class TestAPIClientsProviderCRUD(unittest.TestCase):
    def setUp(self):
        # Patch get_persistent_storage_path to use a temp dir
        self.temp_dir = tempfile.mkdtemp()
        patcher = patch("jrdev.file_operations.file_utils.get_persistent_storage_path", return_value=Path(self.temp_dir))
        self.addCleanup(patcher.stop)
        self.mock_storage_path = patcher.start()
        # Patch JRDEV_PACKAGE_DIR to a temp dir with a default config
        self.package_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.package_dir)
        patcher2 = patch("jrdev.file_operations.file_utils.JRDEV_PACKAGE_DIR", self.package_dir)
        self.addCleanup(patcher2.stop)
        patcher2.start()
        # Write a default api_providers.json in the package config dir
        config_dir = os.path.join(self.package_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        default_providers = {
            "providers": [make_provider_data("openai")]  # always at least one
        }
        with open(os.path.join(config_dir, "api_providers.json"), "w", encoding="utf-8") as f:
            json.dump(default_providers, f)
        # Remove any user_api_providers.json in temp_dir
        user_config = os.path.join(self.temp_dir, "user_api_providers.json")
        if os.path.exists(user_config):
            os.remove(user_config)
        # Now create the APIClients instance
        self.clients = APIClients()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_add_provider(self):
        initial_count = len(self.clients.list_providers())
        new_provider = make_provider_data("testprov", env_key="TESTPROV_KEY", base_url="https://testprov.com")
        self.clients.add_provider(new_provider)
        providers = self.clients.list_providers()
        self.assertEqual(len(providers), initial_count + 1)
        found = [p for p in providers if p.name == "testprov"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].env_key, "TESTPROV_KEY")
        self.assertEqual(found[0].base_url, "https://testprov.com")
        # Check persistence
        user_config = os.path.join(self.temp_dir, "user_api_providers.json")
        with open(user_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        names = [p["name"] for p in data["providers"]]
        self.assertIn("testprov", names)

    def test_edit_provider(self):
        # Add a provider to edit
        new_provider = make_provider_data("editme", env_key="EDITME_KEY", base_url="https://editme.com")
        self.clients.add_provider(new_provider)
        # Edit it
        self.clients.edit_provider("editme", {"env_key": "EDITED_KEY", "base_url": "https://edited.com"})
        providers = self.clients.list_providers()
        found = [p for p in providers if p.name == "editme"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].env_key, "EDITED_KEY")
        self.assertEqual(found[0].base_url, "https://edited.com")
        # Check persistence
        user_config = os.path.join(self.temp_dir, "user_api_providers.json")
        with open(user_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        found = [p for p in data["providers"] if p["name"] == "editme"]
        self.assertEqual(found[0]["env_key"], "EDITED_KEY")
        self.assertEqual(found[0]["base_url"], "https://edited.com")

    def test_remove_provider(self):
        # Add a provider to remove
        new_provider = make_provider_data("toremove", env_key="REMOVE_KEY", base_url="https://remove.com")
        self.clients.add_provider(new_provider)
        providers = self.clients.list_providers()
        self.assertTrue(any(p.name == "toremove" for p in providers))
        # Remove it
        self.clients.remove_provider("toremove")
        providers = self.clients.list_providers()
        self.assertFalse(any(p.name == "toremove" for p in providers))
        # Check persistence
        user_config = os.path.join(self.temp_dir, "user_api_providers.json")
        with open(user_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertFalse(any(p["name"] == "toremove" for p in data["providers"]))

    def test_edit_provider_not_found(self):
        # Should not raise, just log warning
        self.clients.edit_provider("doesnotexist", {"env_key": "NOPE"})
        # No provider added
        self.assertFalse(any(p.name == "doesnotexist" for p in self.clients.list_providers()))

    def test_remove_provider_not_found(self):
        # Should not raise, just log warning
        before = len(self.clients.list_providers())
        self.clients.remove_provider("doesnotexist")
        after = len(self.clients.list_providers())
        self.assertEqual(before, after)

if __name__ == "__main__":
    unittest.main()
