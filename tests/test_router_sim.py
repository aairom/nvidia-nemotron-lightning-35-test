import unittest

from moe_demo.categories import EXPERT_GROUPS
from moe_demo.router_sim import GROUP_SIZE, N_EXPERTS, TOP_K, route_token, simulate, tokenize


class RouterTests(unittest.TestCase):
    def test_top_k_distinct_in_range(self):
        ids = route_token("hello", "coding")
        self.assertEqual(len(ids), TOP_K)
        self.assertEqual(len(set(ids)), TOP_K)
        self.assertTrue(all(0 <= i < N_EXPERTS for i in ids))

    def test_deterministic(self):
        a = simulate("write a python function", "coding")
        b = simulate("write a python function", "coding")
        self.assertEqual(a.expert_counts, b.expert_counts)

    def test_counts_and_shares(self):
        r = simulate("one two three four five", "creative")
        self.assertEqual(sum(r.expert_counts), r.n_tokens * TOP_K)
        self.assertAlmostEqual(sum(r.group_share.values()), 1.0)
        self.assertEqual(len(r.expert_counts), len(EXPERT_GROUPS) * GROUP_SIZE)

    def test_categories_differ_and_prefer_their_group(self):
        text = " ".join(f"tok{i}" for i in range(150))
        code = simulate(text, "coding").group_share
        story = simulate(text, "creative").group_share
        self.assertEqual(max(code, key=code.get), "Code & syntax")
        self.assertEqual(max(story, key=story.get), "Narrative & style")
        self.assertNotEqual(code, story)
        # Soft specialisation: no single group takes everything.
        self.assertLess(max(code.values()), 0.8)

    def test_edge_cases(self):
        self.assertEqual(simulate("", "factual").n_tokens, 1)
        self.assertEqual(len(tokenize("a " * 1000)), 200)
        with self.assertRaises(ValueError):
            simulate("x", "unknown")


if __name__ == "__main__":
    unittest.main()
