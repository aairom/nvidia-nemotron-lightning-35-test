import unittest

from docs_tools import benchmark
from moe_demo.ollama_client import OllamaClient
from tests.stub_ollama import start_stub


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = start_stub()
        cls.client = OllamaClient(cls.url, 10)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_run_case_records_metrics(self):
        rec = benchmark.run_case(self.client, "stub:1", system="s", prompt="hi", temperature=0.5,
                                 think=False, keep_alive="1m", sampler_interval=0.01)
        self.assertEqual(rec["generated_tokens"], 20)
        self.assertEqual(rec["prompt_tokens"], 5)
        self.assertAlmostEqual(rec["tps"], 10.0)
        self.assertTrue(rec["answered"])
        self.assertIn("samples", rec)

    def test_run_case_with_thinking(self):
        rec = benchmark.run_case(self.client, "stub:1", system="", prompt="hi", temperature=1.0,
                                 think=True, keep_alive="1m", sampler_interval=0.01)
        self.assertGreater(rec["reasoning_chars"], 0)

    def test_host_info(self):
        info = benchmark.host_info(self.client, "stub:1")
        self.assertEqual(info["ollama_version"], "9.9.9")
        self.assertEqual(info["model"], "stub:1")
        self.assertIn("python", info)

    def test_prefill_prompt_unique_and_sized(self):
        a, b = benchmark.prefill_prompt(100), benchmark.prefill_prompt(100)
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(a.split()), 100)


if __name__ == "__main__":
    unittest.main()
