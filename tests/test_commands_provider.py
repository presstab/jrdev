import os
import sys
import tempfile
import shutil
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import asyncio

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.commands import provider as provider_cmd
from jrdev.models.api_provider import ApiProvider, DefaultProfiles

# Helper: run async function in sync test
def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

class DummyUI:
    def __init__(self):
        self.printed = []
    def print_text(self, msg, print_type=None):
        self.printed.append((msg, print_type))
    def providers_updated(self):
        self.printed.append(("providers_updated", None))

class DummyApp:
    def __init__(self, clients):
        self.state = MagicMock()
        self.state.clients = clients
        self.ui = DummyUI()
        self.ui_name = "text"
        self.providers_updated = self.ui.providers_updated
        self.refresh_model_list = MagicMock()

class DummyClients:
    def __init__(self):
        self.providers = []
        self.added = []
        self.edited = []
        self.removed = []
    def list_providers(self):
        return self.providers
    def add_provider(self, provider_data):
        self.added.append(provider_data)
        self.providers.append(ApiProvider.from_dict(provider_data))
    def edit_provider(self, name, updated_fields):
        self.edited.append((name, updated_fields))
        for p in self.providers:
            if p.name == name:
                for k, v in updated_fields.items():
                    setattr(p, k, v)
    def remove_provider(self, name):
        self.removed.append(name)
        self.providers = [p for p in self.providers if p.name != name]

class TestProviderCommand(unittest.TestCase):
    def setUp(self):
        self.clients = DummyClients()
        self.app = DummyApp(self.clients)

    def test_help_message(self):
        run_async(provider_cmd.handle_provider(self.app, ["/provider"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("API Provider Management", out)
        self.assertIn("/provider add", out)
        self.assertIn("/provider edit", out)
        self.assertIn("/provider remove", out)

    def test_list_providers_empty(self):
        run_async(provider_cmd.handle_provider(self.app, ["/provider", "list"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("API Providers:", out)
        # No providers
        self.assertEqual(len(self.app.ui.printed), 1)

    def test_list_providers_some(self):
        self.clients.providers = [
            ApiProvider(name="foo", env_key="FOO_KEY", base_url="https://foo.com", required=True, default_profiles=DefaultProfiles(profiles={}, default_profile="")),
            ApiProvider(name="bar", env_key="BAR_KEY", base_url="https://bar.com", required=True, default_profiles=DefaultProfiles(profiles={}, default_profile=""))
        ]
        run_async(provider_cmd.handle_provider(self.app, ["/provider", "list"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("API Providers:", out)
        self.assertIn("  foo (env_key: FOO_KEY, base_url: https://foo.com)", out)
        self.assertIn("  bar (env_key: BAR_KEY, base_url: https://bar.com)", out)

    def test_add_provider_success(self):
        args = ["/provider", "add", "baz", "BAZ_KEY", "https://baz.com"]
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        self.assertEqual(self.clients.added[0]["name"], "baz")
        self.assertEqual(self.clients.added[0]["env_key"], "BAZ_KEY")
        self.assertEqual(self.clients.added[0]["base_url"], "https://baz.com")
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Provider 'baz' added successfully.", out)
        self.assertIn("providers_updated", [msg for msg, _ in self.app.ui.printed])
        self.app.refresh_model_list.assert_called()

    def test_add_provider_missing_args(self):
        args = ["/provider", "add", "baz", "BAZ_KEY"]  # missing base_url
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Usage: /provider add <name> <env_key_name> <base_url>", out)
        self.assertEqual(len(self.clients.added), 0)

    def test_add_provider_exception(self):
        # Patch add_provider to raise
        self.clients.add_provider = MagicMock(side_effect=Exception("failadd"))
        args = ["/provider", "add", "baz", "BAZ_KEY", "https://baz.com"]
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Error adding provider: failadd", out)

    def test_edit_provider_success(self):
        self.clients.providers = [ApiProvider(name="editme", env_key="EDITME_KEY", base_url="https://editme.com", required=True, default_profiles=DefaultProfiles(profiles={}, default_profile=""))]
        args = ["/provider", "edit", "editme", "NEW_KEY", "https://new.com"]
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        self.assertEqual(self.clients.edited[0][0], "editme")
        self.assertEqual(self.clients.edited[0][1]["env_key"], "NEW_KEY")
        self.assertEqual(self.clients.edited[0][1]["base_url"], "https://new.com")
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Provider 'editme' edited successfully.", out)
        self.assertIn("providers_updated", [msg for msg, _ in self.app.ui.printed])

    def test_edit_provider_missing_args(self):
        args = ["/provider", "edit", "editme", "NEW_KEY"]  # missing base_url
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Usage: /provider edit <name> <new_env_key_name> <new_base_url>", out)
        self.assertEqual(len(self.clients.edited), 0)

    def test_edit_provider_exception(self):
        self.clients.edit_provider = MagicMock(side_effect=Exception("failedit"))
        args = ["/provider", "edit", "editme", "NEW_KEY", "https://new.com"]
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Error editing provider: failedit", out)

    def test_remove_provider_success(self):
        self.clients.providers = [ApiProvider(name="toremove", env_key="KEY", base_url="https://rm.com", required=True, default_profiles=DefaultProfiles(profiles={}, default_profile=""))]
        args = ["/provider", "remove", "toremove"]
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        self.assertIn("toremove", self.clients.removed)
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Provider 'toremove' removed successfully.", out)
        self.assertIn("providers_updated", [msg for msg, _ in self.app.ui.printed])
        self.app.refresh_model_list.assert_called()

    def test_remove_provider_missing_args(self):
        args = ["/provider", "remove"]  # missing name
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Usage: /provider remove <name>", out)
        self.assertEqual(len(self.clients.removed), 0)

    def test_remove_provider_exception(self):
        self.clients.remove_provider = MagicMock(side_effect=Exception("failrm"))
        args = ["/provider", "remove", "toremove"]
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Error removing provider: failrm", out)

    def test_unknown_command(self):
        args = ["/provider", "unknowncmd"]
        run_async(provider_cmd.handle_provider(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Unknown command: unknowncmd", out)
        self.assertIn("Type /provider help for usage.", out)

if __name__ == "__main__":
    unittest.main()
