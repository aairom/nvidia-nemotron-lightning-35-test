import unittest

from moe_demo.engine import (build_messages, build_options, reasoning_share, resolve_think,
                             stream_answer)
from moe_demo.ollama_client import OllamaClient
from tests.stub_ollama import start_stub


class OptionTests(unittest.TestCase):
    def test_build_options_ok(self):
        o = build_options(0.7, 0.9, 4096, 256)
        self.assertEqual(o, {"temperature": 0.7, "top_p": 0.9, "num_ctx": 4096, "num_predict": 256})

    def test_build_options_validation(self):
        for args in [(-0.1, .9, 4096, 1), (2.1, .9, 4096, 1), (1, 0, 4096, 1), (1, 1.1, 4096, 1), (1, .9, 100, 1)]:
            with self.assertRaises(ValueError):
                build_options(*args)

    def test_resolve_think(self):
        self.assertIs(resolve_think("Auto (per category)", "off"), False)
        self.assertEqual(resolve_think("Auto (per category)", "medium"), "medium")
        self.assertIs(resolve_think("On", "off"), True)
        self.assertIs(resolve_think("Off", "medium"), False)
        self.assertEqual(resolve_think("Medium", "off"), "medium")
        with self.assertRaises(ValueError):
            resolve_think("Bogus", "off")

    def test_build_messages(self):
        hist = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"},
                {"role": "assistant", "content": ""}]
        m = build_messages("sys", hist, "q", True)
        self.assertEqual([x["role"] for x in m], ["system", "user", "assistant", "user"])
        m = build_messages("", hist, "q", False)
        self.assertEqual(m, [{"role": "user", "content": "q"}])

    def test_history_truncated(self):
        hist = [{"role": "user", "content": str(i)} for i in range(50)]
        self.assertEqual(len(build_messages("", hist, "q", True, max_turns=2)), 5)

    def test_reasoning_share(self):
        self.assertEqual(reasoning_share("", ""), 0.0)
        self.assertEqual(reasoning_share("ab", "ab"), 0.5)


class StreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, url = start_stub()
        cls.c = OllamaClient(url, 5)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_stream_answer_final_metrics(self):
        ups = list(stream_answer(self.c, "stub:1", [{"role": "user", "content": "hi"}], {}, True, "1m"))
        last = ups[-1]
        self.assertEqual(last.content, "Hello")
        self.assertEqual(last.thinking, "hmm ")
        self.assertIsNotNone(last.final)
        self.assertAlmostEqual(last.final.tokens_per_second, 10.0)
        self.assertEqual(last.final.prompt_tokens, 5)
        self.assertAlmostEqual(last.final.load_seconds, 1.0)
        self.assertTrue(all(u.final is None for u in ups[:-1]))

    def test_options_forwarded(self):
        opts = build_options(0.3, 0.8, 2048, 64)
        list(stream_answer(self.c, "stub:1", [{"role": "user", "content": "hi"}], opts, False, "1m"))
        path, req = self.srv.requests[-1]
        self.assertEqual(path, "/api/chat")
        self.assertEqual(req["options"]["temperature"], 0.3)
        self.assertEqual(req["options"]["num_ctx"], 2048)
        self.assertIs(req["think"], False)


if __name__ == "__main__":
    unittest.main()
