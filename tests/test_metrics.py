import unittest

from moe_demo.metrics import RunMetrics, active_fractions, from_stats


class MetricsTests(unittest.TestCase):
    def test_from_stats(self):
        m = from_stats({"prompt_eval_count": 10, "eval_count": 100, "eval_duration": 4_000_000_000,
                        "prompt_eval_duration": 1_000_000_000, "load_duration": 2_000_000_000,
                        "total_duration": 7_000_000_000}, ttft=1.5, wall=7.2)
        self.assertEqual(m.tokens_per_second, 25.0)
        self.assertEqual(m.prompt_tokens_per_second, 10.0)
        self.assertEqual(m.total_tokens, 110)
        self.assertEqual(m.load_seconds, 2.0)
        self.assertEqual(m.to_dict()["tokens_per_second"], 25.0)

    def test_missing_and_zero_values(self):
        m = from_stats({})
        self.assertEqual(m.tokens_per_second, 0.0)
        self.assertEqual(RunMetrics().prompt_tokens_per_second, 0.0)
        self.assertEqual(from_stats({"eval_count": None}).generated_tokens, 0)

    def test_active_fractions(self):
        f = active_fractions()
        self.assertAlmostEqual(f["active_param_fraction"], 0.1)
        self.assertAlmostEqual(f["active_expert_fraction"], 6 / 128)


if __name__ == "__main__":
    unittest.main()
