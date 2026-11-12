"""Headless smoke test of the Streamlit script using Streamlit's AppTest harness."""
import os
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.stub_ollama import start_stub

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class AppSmoke(unittest.TestCase):
    def test_runs_offline_without_exception(self):
        os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:1"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
        finally:
            del os.environ["OLLAMA_BASE_URL"]
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(any("offline" in e.value.lower() for e in at.sidebar.error))

    def test_example_click_with_stub(self):
        srv, url = start_stub()
        os.environ["OLLAMA_BASE_URL"], os.environ["OLLAMA_MODEL"] = url, "stub:1"
        try:
            at = AppTest.from_file(APP, default_timeout=30).run()
            self.assertFalse(at.exception, at.exception)
            self.assertTrue(any("online" in s.value.lower() for s in at.sidebar.success))
            next(b for b in at.button if b.key == "ex_coding_0").click().run()
            self.assertFalse(at.exception, at.exception)
            self.assertEqual([m.name for m in at.chat_message], ["user", "assistant"])
            self.assertIn("Hello", at.chat_message[1].markdown[-1].value)
            # Free-text prompt keeps working and builds history.
            at.chat_input[0].set_value("Summarize this: a b c").run()
            self.assertFalse(at.exception, at.exception)
            self.assertEqual(len(at.chat_message), 4)
        finally:
            srv.shutdown()
            del os.environ["OLLAMA_BASE_URL"], os.environ["OLLAMA_MODEL"]


if __name__ == "__main__":
    unittest.main()
