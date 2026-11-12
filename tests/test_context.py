import unittest

from docs_tools.context import CHAPTERS, Ctx, Raw, code_inline, grid2, kpis, legend_key, rich, table


class HelperTests(unittest.TestCase):
    def test_rich_whitelist(self):
        out = rich("<b>x</b> <code>y</code> <script>z</script> & <i>w</i>")
        self.assertIn("<b>x</b>", out)
        self.assertIn("<code>y</code>", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("&amp;", out)

    def test_table_escapes_unless_raw(self):
        html = table(["<h>", "n"], [["<x>", Raw("<em>ok</em>")], ["a", 1]], num_cols=(1,), caption="cap")
        self.assertIn("&lt;h&gt;", html)
        self.assertIn("&lt;x&gt;", html)
        self.assertIn("<em>ok</em>", html)
        self.assertIn('<td class="n">1</td>', html)
        self.assertIn("<caption>cap</caption>", html)

    def test_kpis_grid_legend_inline(self):
        self.assertIn("<b>46</b><span>tok/s</span>", kpis([("46", "tok/s")]))
        self.assertTrue(grid2("<p>a</p>", "<p>b</p>").startswith('<div class="grid2">'))
        self.assertEqual(legend_key().count("<span"), 5)
        self.assertEqual(code_inline("a<b"), "<code>a&lt;b</code>")


class CtxTests(unittest.TestCase):
    def test_figure_numbering_resets_per_chapter(self):
        c = Ctx()
        c.start(2)
        c.fig("diagram", "fig-a", "A", "")
        c.fig("chart", "fig-b", "B", "")
        c.start(3)
        c.fig("concept", "fig-c", "C", "")
        self.assertEqual(c.new_labels, {"fig-a": "Figure 2-1", "fig-b": "Figure 2-2", "fig-c": "Figure 3-1"})
        self.assertEqual(c.captions["fig-b"], "B")

    def test_duplicate_figure_id(self):
        c = Ctx()
        c.start(1)
        c.fig("diagram", "fig-a", "A", "")
        with self.assertRaises(ValueError):
            c.fig("diagram", "fig-a", "A", "")

    def test_xref_strict_raises(self):
        c = Ctx(strict=True)
        with self.assertRaises(KeyError):
            c.xref("fig-missing")
        with self.assertRaises(KeyError):
            c.xref("s9-missing")

    def test_xref_lenient_and_resolved(self):
        self.assertIn(">fig-x<", Ctx().xref("fig-x"))
        c = Ctx({"fig-a": "Figure 1-1"}, strict=True, titles={"s1-t": "Title"})
        self.assertIn('href="#fig-a">Figure 1-1<', c.xref("fig-a"))
        self.assertIn(">Title<", c.xref("s1-t"))
        self.assertIn(">Chapter 4<", c.xref("ch4"))
        self.assertIn(">custom<", c.xref("ch4", "custom"))

    def test_sections_and_head(self):
        c = Ctx()
        c.start(2)
        self.assertIn("2.1 First", c.h3("a", "First"))
        self.assertIn("2.2 Second", c.h3("b", "Second"))
        self.assertIn('id="ch2"', c.head(2, "lead"))
        self.assertEqual([a for _, a, _ in c.sections], ["s2-a", "s2-b"])

    def test_evidence_missing_placeholder(self):
        self.assertIn("not found", Ctx().evidence("no_such_capture.txt"))

    def test_chapters_constant(self):
        self.assertEqual([n for n, _ in CHAPTERS], list(range(1, 9)))


if __name__ == "__main__":
    unittest.main()
