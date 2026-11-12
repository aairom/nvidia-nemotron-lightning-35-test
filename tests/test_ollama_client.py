import unittest

from moe_demo.ollama_client import (OllamaClient, OllamaConnectionError, OllamaError,
                                    OllamaModelNotFound)
from tests.stub_ollama import start_stub


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = start_stub()
        cls.c = OllamaClient(cls.url, timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_status_endpoints(self):
        self.assertEqual(self.c.version(), "9.9.9")
        self.assertTrue(self.c.is_alive())
        self.assertEqual(self.c.list_models(), ["stub:1"])

    def test_preload_unload_and_loaded_info(self):
        self.assertIsNone(self.c.loaded_info("stub:1"))
        self.c.preload("stub:1")
        self.assertEqual(self.c.loaded_info("stub:1")["size"], 123)
        self.c.unload("stub:1")
        self.assertIsNone(self.c.loaded_info("stub:1"))

    def test_chat_stream_content_and_stats(self):
        ev = list(self.c.chat_stream("stub:1", [{"role": "user", "content": "hi"}], think=False))
        self.assertEqual("".join(e.text for e in ev if e.kind == "content"), "Hello")
        self.assertEqual(ev[-1].kind, "done")
        self.assertEqual(ev[-1].stats["eval_count"], 20)

    def test_chat_stream_thinking(self):
        ev = list(self.c.chat_stream("stub:1", [{"role": "user", "content": "hi"}], think=True))
        self.assertEqual([e.kind for e in ev][0], "thinking")

    def test_unknown_model(self):
        with self.assertRaises(OllamaModelNotFound):
            list(self.c.chat_stream("nope", [{"role": "user", "content": "hi"}]))

    def test_http_error(self):
        with self.assertRaises(OllamaError) as cm:
            list(self.c.chat_stream("stub:1", [{"role": "user", "content": "boom"}]))
        self.assertIn("kaboom", str(cm.exception))

    def test_error_mid_stream(self):
        with self.assertRaises(OllamaError):
            list(self.c.chat_stream("stub:1", [{"role": "user", "content": "midstream"}]))

    def test_connection_refused(self):
        dead = OllamaClient("http://127.0.0.1:1", timeout=1)
        self.assertFalse(dead.is_alive())
        with self.assertRaises(OllamaConnectionError):
            dead.version()
        with self.assertRaises(OllamaConnectionError):
            list(dead.chat_stream("m", [{"role": "user", "content": "x"}]))


if __name__ == "__main__":
    unittest.main()
