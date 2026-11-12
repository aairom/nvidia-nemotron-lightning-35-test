import unittest

from docs_tools import theme


class CssTests(unittest.TestCase):
    def test_inline_code_style_is_reset_inside_pre(self):
        # Regression: the light inline-code background used to leak into dark listings.
        self.assertIn("pre code{background:none", theme.CSS)


class FigureTests(unittest.TestCase):
    def test_kinds_and_badge(self):
        for kind, badge in theme._KINDS.items():
            html = theme.figure(kind, "fig-x", "cap", "<p>b</p>", label="Figure 1-1")
            self.assertIn(f'class="{kind}"', html)
            self.assertIn(badge, html)
            self.assertIn("Figure 1-1.", html)

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            theme.figure("nope", "x", "c", "b")

    def test_caption_escaped_and_label_defaults_to_id(self):
        html = theme.figure("diagram", "fig-x", "<b>x</b>", "")
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertIn("<b>fig-x.</b>", html)

    def test_shot_has_browser_chrome(self):
        html = theme.figure("shot", "fig-s", "c", "", url="http://example.test")
        self.assertIn("browser", html)
        self.assertIn("http://example.test", html)


class ShotTests(unittest.TestCase):
    def test_pins_boxes_legend(self):
        html = theme.shot("fig-s", "c", "data:image/jpeg;base64,AAA",
                          pins=[(10, 20, "first"), (30, 40, "second")], boxes=[(1, 2, 3, 4)])
        self.assertEqual(html.count('class="pin"'), 2)
        self.assertIn("left:10%;top:20%", html)
        self.assertIn("left:1%;top:2%;width:3%;height:4%", html)
        self.assertIn("<span>second</span>", html)

    def test_without_pins_has_no_legend(self):
        self.assertNotIn("legend", theme.shot("fig-s", "c", "data:x").replace('class="legend-key"', ""))


class TerminalTests(unittest.TestCase):
    def test_colouring_and_escaping(self):
        html = theme.term_block("t", "$ run <it>\ntest PASSED\nsomething FAILED\nplain")
        self.assertIn('<span class="cmd">$ run &lt;it&gt;</span>', html)
        self.assertIn('<span class="ok">test PASSED</span>', html)
        self.assertIn('<span class="bad">something FAILED</span>', html)
        self.assertIn("\nplain</pre>", html)

    def test_bad_wins_over_good(self):
        html = theme.term_block("t", "1 passed, 1 FAILED")
        self.assertIn('class="bad"', html)


class CodeTests(unittest.TestCase):
    def test_highlight(self):
        out = theme.highlight_python('def f():\n    return "a<b"  # note\n    x = 42')
        self.assertIn('<span class="k">def</span>', out)
        self.assertIn('<span class="s">&quot;a&lt;b&quot;</span>', out.replace("&#x27;", "'"))
        self.assertIn('<span class="c"># note</span>', out)
        self.assertIn('<span class="n">42</span>', out)

    def test_code_wrapper(self):
        self.assertIn("codecap", theme.code("x = 1", caption="c"))
        self.assertNotIn("<span", theme.code("<b>", lang="text"))

    def test_callout(self):
        self.assertIn("callout warn", theme.callout("warn", "T", "<p>x</p>"))
        with self.assertRaises(KeyError):
            theme.callout("other", "T", "")


if __name__ == "__main__":
    unittest.main()
