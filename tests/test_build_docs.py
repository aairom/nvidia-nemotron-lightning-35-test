import re
import unittest

from docs_tools import build_docs
from docs_tools.context import CHAPTERS, Ctx


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html, cls.ctx = build_docs.build(strict=True)

    def test_all_chapters_present(self):
        for n, title in CHAPTERS:
            self.assertIn(f'id="ch{n}"', self.html)

    def test_every_internal_link_resolves(self):
        ids = set(re.findall(r'id="([^"]+)"', self.html))
        for target in re.findall(r'href="#([^"]+)"', self.html):
            self.assertIn(target, ids, f"dead link #{target}")

    def test_no_external_resources(self):
        for src in re.findall(r'src="([^"]+)"', self.html):
            self.assertTrue(src.startswith("data:image/"), src[:40])
        self.assertNotIn("<script", self.html)
        self.assertNotRegex(self.html, r'<link[^>]+href=')

    def test_every_figure_labelled(self):
        self.assertGreaterEqual(len(self.ctx.new_labels), 40)
        for fid, label in self.ctx.new_labels.items():
            self.assertIn(f'id="{fid}"', self.html)
            self.assertIn(f"<b>{label}.</b>", self.html)

    def test_no_missing_evidence_placeholders(self):
        self.assertNotIn("not found - run", self.html)

    def test_footer_and_cover(self):
        self.assertIn("Made with IBM Bob", self.html)
        self.assertIn('class="cover"', self.html)

    def test_pager_edges(self):
        self.assertIn("Back to top", build_docs.pager(len(CHAPTERS) - 1))
        self.assertIn("<span></span>", build_docs.pager(0))

    def test_toc_lists_sections(self):
        toc = build_docs.build_toc(self.ctx)
        self.assertEqual(toc.count('class="sec"'), len(self.ctx.sections))

    def test_main_writes_file(self):
        out = build_docs.OUT
        orig = out.read_text(encoding="utf-8") if out.exists() else None
        try:
            self.assertEqual(build_docs.main([]), 0)
            self.assertTrue(out.stat().st_size > 100_000)
        finally:
            if orig is not None:
                out.write_text(orig, encoding="utf-8")

    def test_strict_mode_detects_bad_reference(self):
        with self.assertRaises(KeyError):
            Ctx(strict=True).xref("fig-does-not-exist")


if __name__ == "__main__":
    unittest.main()
