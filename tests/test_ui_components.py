import unittest

from moe_demo import ui_components as ui
from moe_demo.metrics import RunMetrics
from moe_demo.router_sim import simulate


class UiTests(unittest.TestCase):
    def test_metric_cards_empty_final_live(self):
        self.assertIn("No request yet", ui.metric_cards(None))
        final = ui.metric_cards(RunMetrics(generated_tokens=50, generation_seconds=2, wall_seconds=3),
                                reasoning_pct=0.25)
        self.assertIn("25.0", final)
        self.assertIn("Reasoning share", final)
        live = ui.metric_cards(None, live_tps=12.3, live_chunks=5, elapsed=1.0, ttft=0.2)
        self.assertIn("12.3", live)

    def test_html_escaped(self):
        self.assertNotIn("<script>", ui._card("<script>", "<b>", "<i>", "<x>"))

    def test_expert_panels(self):
        r = simulate("def f(): return 1", "coding")
        self.assertEqual(ui.expert_heatmap(r).count('class="c"'), 128)
        self.assertIn("Code &amp; syntax", ui.group_bars(r))
        self.assertIn("chip", ui.top_group_chips(r))
        self.assertIn("6 of 128", ui.sparsity_caption())



if __name__ == "__main__":
    unittest.main()
