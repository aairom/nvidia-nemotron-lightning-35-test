import unittest

from moe_demo.categories import CATEGORIES
from moe_demo.help_text import MOE_GUIDE, PARAM_GUIDE, TOOLTIPS


class HelpTextTests(unittest.TestCase):
    def test_tooltips_cover_controls_and_metrics(self):
        for k in ("temperature", "top_p", "num_ctx", "num_predict", "think", "tps", "ttft", "load", "wall"):
            self.assertTrue(TOOLTIPS[k])

    def test_guides_explain_moe(self):
        self.assertIn("Mixture of Experts", MOE_GUIDE)
        self.assertIn("6 of 128", MOE_GUIDE)
        self.assertIn("Illustrative", MOE_GUIDE)
        self.assertTrue(PARAM_GUIDE)

    def test_every_category_explains_its_experts(self):
        for c in CATEGORIES.values():
            self.assertGreater(len(c.why), 40)


if __name__ == "__main__":
    unittest.main()
