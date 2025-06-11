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

from jrdev.models import model_utils

def make_model(name, provider="openai", is_think=False, input_cost=1, output_cost=2, context_tokens=4096):
    return {
        "name": name,
        "provider": provider,
        "is_think": is_think,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "context_tokens": context_tokens
    }

class TestModelUtils(unittest.TestCase):
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
        # Write a default model_list.json in the package config dir
        config_dir = os.path.join(self.package_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        self.default_models = [make_model("gpt-4"), make_model("gpt-3.5")]  # always at least two
        with open(os.path.join(config_dir, "model_list.json"), "w", encoding="utf-8") as f:
            json.dump({"models": self.default_models}, f)
        # Remove any user_models.json in temp_dir
        user_config = os.path.join(self.temp_dir, "user_models.json")
        if os.path.exists(user_config):
            os.remove(user_config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def user_models_path(self):
        return os.path.join(self.temp_dir, "user_models.json")

    def test_ensure_user_models_config_exists_creates_file(self):
        user_config = self.user_models_path()
        self.assertFalse(os.path.exists(user_config))
        model_utils._ensure_user_models_config_exists()
        self.assertTrue(os.path.exists(user_config))
        with open(user_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("models", data)
        self.assertEqual(data["models"], self.default_models)

    def test_ensure_user_models_config_exists_does_not_overwrite(self):
        user_config = self.user_models_path()
        # Write a custom file
        custom_models = [make_model("custom")] 
        with open(user_config, "w", encoding="utf-8") as f:
            json.dump({"models": custom_models}, f)
        model_utils._ensure_user_models_config_exists()
        with open(user_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["models"], custom_models)

    def test_load_models_creates_file_if_missing(self):
        user_config = self.user_models_path()
        self.assertFalse(os.path.exists(user_config))
        models = model_utils.load_models()
        self.assertTrue(os.path.exists(user_config))
        self.assertEqual(models, self.default_models)

    def test_load_models_reads_existing(self):
        user_config = self.user_models_path()
        custom_models = [make_model("foo"), make_model("bar")] 
        with open(user_config, "w", encoding="utf-8") as f:
            json.dump({"models": custom_models}, f)
        models = model_utils.load_models()
        self.assertEqual(models, custom_models)

    def test_load_models_returns_empty_on_malformed(self):
        user_config = self.user_models_path()
        with open(user_config, "w", encoding="utf-8") as f:
            f.write("not a json")
        models = model_utils.load_models()
        self.assertEqual(models, [])

    def test_load_models_returns_empty_on_missing_models_key(self):
        user_config = self.user_models_path()
        with open(user_config, "w", encoding="utf-8") as f:
            json.dump({"notmodels": []}, f)
        models = model_utils.load_models()
        self.assertEqual(models, [])

    def test_load_models_returns_empty_on_models_not_list(self):
        user_config = self.user_models_path()
        with open(user_config, "w", encoding="utf-8") as f:
            json.dump({"models": "notalist"}, f)
        models = model_utils.load_models()
        self.assertEqual(models, [])

    def test_load_models_returns_empty_on_models_missing_name(self):
        user_config = self.user_models_path()
        with open(user_config, "w", encoding="utf-8") as f:
            json.dump({"models": [{"provider": "openai"}]}, f)
        models = model_utils.load_models()
        self.assertEqual(models, [])

    def test_save_models_overwrites_file(self):
        user_config = self.user_models_path()
        # Write initial
        with open(user_config, "w", encoding="utf-8") as f:
            json.dump({"models": [make_model("old")]}, f)
        new_models = [make_model("new1"), make_model("new2")] 
        model_utils.save_models(new_models)
        with open(user_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["models"], new_models)

    def test_save_models_creates_file_if_missing(self):
        user_config = self.user_models_path()
        if os.path.exists(user_config):
            os.remove(user_config)
        new_models = [make_model("a"), make_model("b")] 
        model_utils.save_models(new_models)
        self.assertTrue(os.path.exists(user_config))
        with open(user_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["models"], new_models)

if __name__ == "__main__":
    unittest.main()
