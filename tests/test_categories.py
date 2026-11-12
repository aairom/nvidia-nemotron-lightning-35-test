import unittest

from moe_demo.categories import CATEGORIES, EXPERT_GROUPS, classify


class CategoryTests(unittest.TestCase):
    def test_five_categories_with_examples(self):
        self.assertGreaterEqual(len(CATEGORIES), 5)
        for c in CATEGORIES.values():
            self.assertGreaterEqual(len(c.examples), 3)
            self.assertTrue(set(c.expert_affinity) <= set(EXPERT_GROUPS))
            self.assertIn(c.think, ("off", "on", "medium"))
            self.assertTrue(0 <= c.temperature <= 2)

    def test_examples_classify_to_own_category(self):
        for key, c in CATEGORIES.items():
            hits = sum(classify(e.prompt)[0] == key for e in c.examples)
            self.assertGreaterEqual(hits, 2, f"{key}: only {hits}/3 examples classified correctly")

    def test_classify_fallback_and_code(self):
        self.assertEqual(classify("zzz qqq")[0], "factual")
        self.assertEqual(classify("```\nx=1\n```")[0], "coding")
        self.assertEqual(classify("please summarize this")[0], "summarization")


if __name__ == "__main__":
    unittest.main()
