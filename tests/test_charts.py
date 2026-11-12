import unittest

from docs_tools import charts

EVIL = "<script>x</script>"


class ChartTests(unittest.TestCase):
    def assert_svg(self, s):
        self.assertTrue(s.startswith("<svg") and s.endswith("</svg>"))
        self.assertNotIn(EVIL, s)

    def test_nice_max_and_fmt(self):
        self.assertEqual(charts._nice_max(0), 1.0)
        self.assertEqual(charts._nice_max(46), 50)
        self.assertEqual(charts._nice_max(101), 200)
        self.assertEqual(charts._fmt(3), "3")
        self.assertEqual(charts._fmt(3.25), "3.2")
        self.assertEqual(charts._fmt(250.4), "250")

    def test_bar_chart_escapes_and_wraps_labels(self):
        s = charts.bar_chart([EVIL, "a b c d"], [3, 9], title=EVIL, unit=" s")
        self.assert_svg(s)
        self.assertEqual(s.count("<rect"), 2)
        self.assertIn("&lt;script&gt;", s)

    def test_bar_chart_custom_values(self):
        s = charts.bar_chart(["a"], [1], title="t", note_values=["custom"], colors=["red"])
        self.assertIn("custom", s)
        self.assertIn('fill="red"', s)

    def test_bar_chart_rotates_labels_when_crowded(self):
        labels = [f"module_{i:02d}_long_name" for i in range(19)]
        s = charts.bar_chart(labels, list(range(1, 20)), title="t", width=900)
        self.assertEqual(s.count("rotate(-40"), 19)
        self.assertNotIn("rotate(-40", charts.bar_chart(["a", "b"], [1, 2], title="t"))

    def test_radar_has_side_padding_for_long_labels(self):
        s = charts.radar_chart(["World knowledge", "b", "c"], [1, 1, 1], title="t", size=300)
        self.assertIn('viewBox="0 0 390 300"', s)

    def test_hbar_stacked_legend_wraps(self):
        names = [f"segment {i}" for i in range(8)]
        s = charts.hbar_stacked(["r1", "r2"], [[1] * 8, [0] * 8], names, title="t")
        self.assert_svg(s)
        self.assertEqual(s.count('rx="2"'), 8)

    def test_line_chart(self):
        s = charts.line_chart([("a", [0, 1, 2], [1, 2, 3]), ("b", [0, 1], [2, 1])], title="t",
                              xlabel=EVIL, ylabel="y", markers=True)
        self.assert_svg(s)
        self.assertEqual(s.count("<polyline"), 2)
        self.assertEqual(s.count("<circle"), 5)

    def test_line_chart_empty(self):
        self.assert_svg(charts.line_chart([], title="t", xlabel="x", ylabel="y"))

    def test_radar(self):
        s = charts.radar_chart(["a", "b", "c"], [0.1, 0.5, 1.0], title=EVIL)
        self.assert_svg(s)
        self.assertIn("<polygon", s)

    def test_heatmap(self):
        s = charts.matrix_heatmap(["r1", "r2"], [EVIL, "c2"], [[0, 1], [0.5, 0.2]], title="t")
        self.assert_svg(s)
        self.assertEqual(s.count("fill-opacity"), 4)

    def test_diagram_and_sequence(self):
        nodes = {"a": (0, 0, 100, 40, "A\nsub", "ui"), "b": (200, 0, 100, 40, EVIL, "logic")}
        s = charts.diagram(nodes, [("a", "b", "go"), ("b", "a", "")], width=320, height=60, title="t")
        self.assert_svg(s)
        self.assertEqual(s.count("<line"), 2)
        q = charts.sequence_diagram(["x", "y"], [(0, 1, "call"), (1, 0, "ret"), (0, 0, "self")], title="t")
        self.assert_svg(q)
        self.assertIn("stroke-dasharray", q)

    def test_expert_grid(self):
        s = charts.expert_grid([0, 17, 127], ["g1", "g2"], title="t")
        self.assert_svg(s)
        self.assertEqual(s.count("#fff"), 3)
        self.assertEqual(s.count('class="ax"'), 8)


if __name__ == "__main__":
    unittest.main()
