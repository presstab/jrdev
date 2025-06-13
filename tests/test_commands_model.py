import os
import sys
import tempfile
import shutil
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import asyncio

# Add src to the path so we can import jrdev modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from jrdev.commands import model as model_cmd

# Helper: run async function in sync test
def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

class DummyUI:
    def __init__(self):
        self.printed = []
    def print_text(self, msg, print_type=None):
        self.printed.append((msg, print_type))

class DummyApp:
    def __init__(self, models=None, model=None):
        self._models = models or []
        self._model_names = [m["name"] for m in self._models]
        self.state = MagicMock()
        self.state.model = model
        self.ui = DummyUI()
        self.logger = MagicMock()
        self.set_model_calls = []
        self.added_models = []
        self.removed_models = []
        self.edited_models = []
        self.failed_remove = False
    def get_model_names(self):
        return [m["name"] for m in self._models]
    def get_models(self):
        return list(self._models)
    def set_model(self, name):
        self.state.model = name
        self.set_model_calls.append(name)
    def add_model(self, name, provider, is_think, input_cost, output_cost, context_window):
        if name in self.get_model_names():
            return False
        self._models.append({
            "name": name,
            "provider": provider,
            "is_think": is_think,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "context_tokens": context_window
        })
        self.added_models.append(name)
        return True
    def remove_model(self, name):
        if self.failed_remove:
            return False
        for i, m in enumerate(self._models):
            if m["name"] == name:
                del self._models[i]
                self.removed_models.append(name)
                return True
        return False
    def edit_model(self, name, provider, is_think, input_cost, output_cost, context_window):
        for i, m in enumerate(self._models):
            if m["name"] == name:
                self._models[i] = {
                    "name": name,
                    "provider": provider,
                    "is_think": is_think,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "context_tokens": context_window
                }
                self.edited_models.append(name)
                return True
        return False

class TestModelCommand(unittest.TestCase):
    def setUp(self):
        self.default_models = [
            {"name": "gpt-4", "provider": "openai", "is_think": True, "input_cost": 1, "output_cost": 2, "context_tokens": 8192},
            {"name": "gpt-3.5", "provider": "openai", "is_think": False, "input_cost": 1, "output_cost": 2, "context_tokens": 4096}
        ]
        self.app = DummyApp(models=[m.copy() for m in self.default_models], model="gpt-4")

    def test_usage_message_and_current_model(self):
        run_async(model_cmd.handle_model(self.app, ["/model"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Current chat model: gpt-4", out)
        self.assertIn("/model list", out)
        self.assertIn("Available models: gpt-4, gpt-3.5", out)

    def test_list_models(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "list"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Available models (from your user_models.json):", out)
        self.assertIn("  - gpt-4", out)
        self.assertIn("  - gpt-3.5", out)

    def test_list_models_empty(self):
        app = DummyApp(models=[])
        run_async(model_cmd.handle_model(app, ["/model", "list"], "w1"))
        out = "\n".join(msg for msg, _ in app.ui.printed)
        self.assertIn("No models available in your user configuration", out)

    def test_set_model_success(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "set", "gpt-3.5"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Chat model set to: gpt-3.5", out)
        self.assertEqual(self.app.state.model, "gpt-3.5")
        self.assertIn("gpt-3.5", self.app.set_model_calls)

    def test_set_model_missing_arg(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "set"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Usage: /model set <model_name>", out)
        self.assertIn("Available models: gpt-4, gpt-3.5", out)

    def test_set_model_not_found(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "set", "notfound"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Error: Model 'notfound' not found in your configuration.", out)
        self.assertIn("Available models: gpt-4, gpt-3.5", out)

    def test_remove_model_success(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "remove", "gpt-3.5"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Removed model gpt-3.5", out)
        self.assertIn("gpt-3.5", self.app.removed_models)
        self.assertFalse(any(m["name"] == "gpt-3.5" for m in self.app.get_models()))

    def test_remove_model_missing_arg(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "remove"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Usage: /model remove <model_name>", out)
        self.assertIn("Available models: gpt-4, gpt-3.5", out)

    def test_remove_model_not_found(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "remove", "notfound"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Error: Model 'notfound' not found in your configuration.", out)

    def test_remove_model_failed(self):
        self.app.failed_remove = True
        run_async(model_cmd.handle_model(self.app, ["/model", "remove", "gpt-4"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Failed to remove model gpt-4", out)
        self.assertNotIn("gpt-4", self.app.removed_models)

    def test_add_model_success(self):
        args = ["/model", "add", "newmodel", "openai", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Successfully added model 'newmodel' (provider: openai)", out)
        self.assertIn("newmodel", self.app.added_models)
        found = [m for m in self.app.get_models() if m["name"] == "newmodel"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["provider"], "openai")
        self.assertEqual(found[0]["is_think"], True)
        self.assertEqual(found[0]["input_cost"], 1)  # 0.10 * 10
        self.assertEqual(found[0]["output_cost"], 3)  # 0.30 * 10
        self.assertEqual(found[0]["context_tokens"], 8192)

    def test_add_model_duplicate(self):
        args = ["/model", "add", "gpt-4", "openai", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("A model named 'gpt-4' already exists in your configuration.", out)
        self.assertNotIn("gpt-4", self.app.added_models)

    def test_add_model_missing_args(self):
        args = ["/model", "add", "foo", "openai", "true", "0.10", "0.30"]  # missing context_window
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Usage: /model add <name> <provider> <is_think> <input_cost> <output_cost> <context_window>", out)
        self.assertNotIn("foo", self.app.added_models)

    def test_add_model_invalid_is_think(self):
        args = ["/model", "add", "foo", "openai", "notabool", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for is_think", out)
        self.assertNotIn("foo", self.app.added_models)

    def test_add_model_invalid_input_cost(self):
        args = ["/model", "add", "foo", "openai", "true", "notafloat", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for input_cost", out)
        self.assertNotIn("foo", self.app.added_models)

    def test_add_model_invalid_output_cost(self):
        args = ["/model", "add", "foo", "openai", "true", "0.10", "notafloat", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for output_cost", out)
        self.assertNotIn("foo", self.app.added_models)

    def test_add_model_invalid_context_window(self):
        args = ["/model", "add", "foo", "openai", "true", "0.10", "0.30", "notanint"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for context_window", out)
        self.assertNotIn("foo", self.app.added_models)

    def test_add_model_failed(self):
        # Patch add_model to return False
        self.app.add_model = MagicMock(return_value=False)
        args = ["/model", "add", "failadd", "openai", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Failed to add model 'failadd' (provider: openai)", out)

    def test_unknown_subcommand(self):
        run_async(model_cmd.handle_model(self.app, ["/model", "unknowncmd"], "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Unknown subcommand: unknowncmd", out)
        self.assertIn("/model list", out)

    def test_add_model_invalid_name_too_short(self):
        args = ["/model", "add", "", "openai", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid model name", out)
        self.assertNotIn("", self.app.added_models)

    def test_add_model_invalid_name_too_long(self):
        long_name = "a" * 65
        args = ["/model", "add", long_name, "openai", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid model name", out)
        self.assertNotIn(long_name, self.app.added_models)

    def test_add_model_invalid_name_bad_chars(self):
        for bad in ["bad\0name", "bad\nname", "bad\rname", "bad\tname", "bad!name", "bad@name", "bad name"]:
            args = ["/model", "add", bad, "openai", "true", "0.10", "0.30", "8192"]
            run_async(model_cmd.handle_model(self.app, args, "w1"))
            out = "\n".join(msg for msg, _ in self.app.ui.printed)
            self.assertIn("Invalid model name", out)
            self.assertNotIn(bad, self.app.added_models)
            self.app.ui.printed.clear()

    def test_add_model_invalid_provider_too_short(self):
        args = ["/model", "add", "validname", "", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid provider name", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_invalid_provider_too_long(self):
        long_provider = "b" * 65
        args = ["/model", "add", "validname", long_provider, "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid provider name", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_invalid_provider_bad_chars(self):
        for bad in ["bad\0provider", "bad\nprovider", "bad\rprovider", "bad\tprovider", "bad!provider", "bad@provider", "bad provider"]:
            args = ["/model", "add", "validname", bad, "true", "0.10", "0.30", "8192"]
            run_async(model_cmd.handle_model(self.app, args, "w1"))
            out = "\n".join(msg for msg, _ in self.app.ui.printed)
            self.assertIn("Invalid provider name", out)
            self.assertNotIn("validname", self.app.added_models)
            self.app.ui.printed.clear()

    def test_add_model_input_cost_too_low(self):
        args = ["/model", "add", "validname", "openai", "true", "-0.01", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("input_cost must be between 0 and 1000", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_input_cost_too_high(self):
        args = ["/model", "add", "validname", "openai", "true", "1000.01", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("input_cost must be between 0 and 1000", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_output_cost_too_low(self):
        args = ["/model", "add", "validname", "openai", "true", "0.10", "-0.01", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("output_cost must be between 0 and 1000", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_output_cost_too_high(self):
        args = ["/model", "add", "validname", "openai", "true", "0.10", "1000.01", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("output_cost must be between 0 and 1000", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_context_window_too_low(self):
        args = ["/model", "add", "validname", "openai", "true", "0.10", "0.30", "0"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("context_window must be between 1 and 1,000,000,000", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_context_window_too_high(self):
        args = ["/model", "add", "validname", "openai", "true", "0.10", "0.30", "1000000001"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("context_window must be between 1 and 1,000,000,000", out)
        self.assertNotIn("validname", self.app.added_models)

    def test_add_model_is_think_case_insensitive(self):
        # Should succeed for various true/false values
        for val, expected in [("TRUE", True), ("True", True), ("1", True), ("yes", True), ("on", True),
                              ("FALSE", False), ("False", False), ("0", False), ("no", False), ("off", False)]:
            args = ["/model", "add", f"model_{val}", "openai", val, "0.10", "0.30", "8192"]
            run_async(model_cmd.handle_model(self.app, args, "w1"))
            self.assertIn(f"model_{val}", self.app.added_models)
        # Clean up for next tests
        self.app.added_models.clear()
        self.app._models = [m.copy() for m in self.default_models]

    # Edit model tests
    def test_edit_model_success(self):
        args = ["/model", "edit", "gpt-4", "newprovider", "false", "0.20", "0.60", "16384"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        model = next(m for m in self.app.get_models() if m["name"] == "gpt-4")
        self.assertEqual(model["provider"], "newprovider")
        self.assertEqual(model["is_think"], False)
        self.assertEqual(model["input_cost"], 2)  # 0.20 * 10
        self.assertEqual(model["output_cost"], 6)  # 0.60 * 10
        self.assertEqual(model["context_tokens"], 16384)
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Successfully edited model 'gpt-4' (provider: newprovider)", out)

    def test_edit_model_missing_args(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "0.10", "0.30"]  # missing context_window
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Usage: /model edit <name> <provider> <is_think> <input_cost> <output_cost> <context_window>", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_not_found(self):
        args = ["/model", "edit", "notfound", "openai", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Error: Model 'notfound' not found in your configuration.", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_invalid_is_think(self):
        args = ["/model", "edit", "gpt-4", "openai", "notabool", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for is_think", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_invalid_input_cost(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "notafloat", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for input_cost", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_invalid_output_cost(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "0.10", "notafloat", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for output_cost", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_invalid_context_window(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "0.10", "0.30", "notanint"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid value for context_window", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_invalid_name(self):
        args = ["/model", "edit", "invalid@name", "openai", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid model name", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_invalid_provider(self):
        args = ["/model", "edit", "gpt-4", "invalid@provider", "true", "0.10", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("Invalid provider name", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_input_cost_too_low(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "-0.01", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("input_cost must be between 0 and 1000", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_input_cost_too_high(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "1000.01", "0.30", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("input_cost must be between 0 and 1000", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_output_cost_too_low(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "0.10", "-0.01", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("output_cost must be between 0 and 1000", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_output_cost_too_high(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "0.10", "1000.01", "8192"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("output_cost must be between 0 and 1000", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_context_window_too_low(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "0.10", "0.30", "0"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("context_window must be between 1 and 1,000,000,000", out)
        self.assertEqual(len(self.app.edited_models), 0)

    def test_edit_model_context_window_too_high(self):
        args = ["/model", "edit", "gpt-4", "openai", "true", "0.10", "0.30", "1000000001"]
        run_async(model_cmd.handle_model(self.app, args, "w1"))
        out = "\n".join(msg for msg, _ in self.app.ui.printed)
        self.assertIn("context_window must be between 1 and 1,000,000,000", out)
        self.assertEqual(len(self.app.edited_models), 0)


if __name__ == "__main__":
    unittest.main()