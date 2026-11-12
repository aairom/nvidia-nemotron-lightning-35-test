import os
import tempfile
import unittest
from pathlib import Path

from moe_demo.config import get_settings, load_env_file


class ConfigTests(unittest.TestCase):
    def test_env_file_and_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text('# c\nOLLAMA_TEST_VAR="abc"\nBAD LINE\n')
            os.environ.pop("OLLAMA_TEST_VAR", None)
            load_env_file(p)
            self.assertEqual(os.environ["OLLAMA_TEST_VAR"], "abc")
            os.environ["OLLAMA_TEST_VAR"] = "real"
            load_env_file(p)  # must not override real env
            self.assertEqual(os.environ["OLLAMA_TEST_VAR"], "real")
            del os.environ["OLLAMA_TEST_VAR"]
        load_env_file(Path("/nonexistent/.env"))  # no error

    def test_settings(self):
        os.environ["OLLAMA_BASE_URL"] = "http://example.invalid:1/"
        try:
            self.assertEqual(get_settings().base_url, "http://example.invalid:1")
        finally:
            del os.environ["OLLAMA_BASE_URL"]


if __name__ == "__main__":
    unittest.main()
